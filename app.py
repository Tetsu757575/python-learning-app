import streamlit as st
import pandas as pd
import requests
import io
import contextlib
from datetime import datetime

# ==========================================
# 🌟 初期設定（先生のGASのURLを入力）
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbx2tVGq9CWtpwoxH8sQPT6jgNZTCLAaEN5Xgl_uNvpn26prn3sl77QLZusqzh5GmEa1/exec"

# ==========================================
# 🌟 スプレッドシートへ結果を送信する関数
# ==========================================
def save_result(student_id, q_id, result, base_score=10):
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "student_id": student_id,
        "q_id": q_id,
        "result": result,
        "base_score": base_score
    }
    try:
        requests.post(GAS_URL, json=payload)
    except Exception as e:
        st.error(f"通信エラーが発生しました: {e}")

# ==========================================
# 🌟 メインの画面と機能
# ==========================================
def main():
    st.title("🐍 Pythonプログラミング学習")

    # --- 学籍番号の入力 ---
    student_id = st.sidebar.text_input("学籍番号を入力してください（例: 1001）")
    if not student_id:
        st.warning("👈 左のメニューから学籍番号を入力してスタートしてください！")
        return

    st.write(f"こんにちは、**{student_id}** さん！")

    # --- CSVファイルから問題を読み込む ---
    try:
        # まず世界標準のUTF-8で読み込みを試す
        df = pd.read_csv("questions.csv", encoding="utf-8")
    except UnicodeDecodeError:
        # エラーが出たら、WindowsのExcel特有の文字コード（CP932）で読み直す
        df = pd.read_csv("questions.csv", encoding="cp932")
    except FileNotFoundError:
        st.error("問題データ（questions.csv）が見つかりません。")
        return

    # --- 問題を選択 ---
    q_id = st.selectbox("📝 挑戦する問題を選んでください", df["問題ID"].tolist())
    q_data = df[df["問題ID"] == q_id].iloc[0]

    # --- 配点を取得（空欄なら10点） ---
    base_score = 10
    if "配点" in q_data and pd.notna(q_data["配点"]):
        try:
            base_score = int(str(q_data["配点"]).strip())
        except:
            pass

    # ==========================================
    # 🌟 正解済みチェック（練習モード判定）
    # ==========================================
    # セッション（短期記憶）に「学籍番号＋問題ID」の専用の鍵を作る
    state_key = f"solved_{q_id}_{student_id}"
    is_solved = st.session_state.get(state_key, False)

    st.write("---")
    st.write("### " + str(q_data['問題文']))

    # すでに正解している場合はメッセージを出す
    if is_solved:
        st.success("🎉 この問題は正解済みです！自由にコードを書き換えて「練習」ができます。（得点は追加されません）")

    # ==========================================
    # 1. 選択問題の処理
    # ==========================================
    if q_data['問題種別'] == '選択':
        options = [opt.strip() for opt in str(q_data['選択肢']).split(',')]
        user_choice = st.radio("選択してください:", options)
        
        # ボタンの表示をモードによって切り替える
        button_label = "練習として解答する" if is_solved else "解答する"
        
        if st.button(button_label, type="primary"):
            if user_choice == str(q_data['正解']).strip():
                st.balloons()
                # 本番モード（未正解）の時だけスプレッドシートに点数を記録
                if not is_solved:
                    save_result(student_id, q_id, "正解", base_score)
                    st.session_state[state_key] = True
                    st.rerun() # 画面を更新して練習モードに切り替え
                else:
                    st.success("大正解！（練習モード）")
            else:
                st.error("❌ 不正解...もう一度考えてみよう！")
                st.info(f"💡 ヒント: {q_data['ヒント']}")
                if not is_solved:
                    save_result(student_id, q_id, "不正解", base_score)

    # ==========================================
    # 2. コード記述問題の処理
    # ==========================================
    elif q_data['問題種別'] == 'コード':
        user_code = st.text_area("Pythonコードを入力:", height=150)
        
        # ボタンの表示をモードによって切り替える
        button_label = "▶️ 練習としてコードを実行する" if is_solved else "▶️ コードを実行して解答する"
        
        if st.button(button_label, type="primary"):
            if not user_code:
                st.warning("コードが入力されていません。")
                return

            # --- 必須キーワードのチェック ---
            if "必須キーワード" in q_data and pd.notna(q_data["必須キーワード"]):
                required_words = [w.strip() for w in str(q_data["必須キーワード"]).split(",")]
                missing_words = [w for w in required_words if w not in user_code]
                
                if missing_words:
                    st.error(f"❌ 不正解です。指定されたキーワード（{', '.join(missing_words)}）がコードに含まれていません。")
                    st.info(f"💡 ヒント: {q_data['ヒント']}")
                    if not is_solved:
                        save_result(student_id, q_id, "不正解", base_score)
                    return

            # --- コードの実行と結果の判定 ---
            f = io.StringIO()
            try:
                # ユーザーのコードを実行し、出力をキャッチする
                with contextlib.redirect_stdout(f):
                    exec(user_code, {})
                output = f.getvalue()

                # 結果の判定
                correct_answer = str(q_data['正解']).strip()
                if output.strip() == correct_answer:
                    st.balloons()
                    # 本番モード（未正解）の時だけスプレッドシートに点数を記録
                    if not is_solved:
                        save_result(student_id, q_id, "正解", base_score)
                        st.session_state[state_key] = True
                        st.rerun() # 画面を更新して練習モードに切り替え
                    else:
                        st.success("🎉 大正解！（練習モード）")
                        st.code(output, language="text")
                else:
                    st.error("❌ 不正解です。")
                    st.write("▼ 実行結果")
                    st.code(output, language="text")
                    st.info(f"💡 ヒント: {q_data['ヒント']}")
                    if not is_solved:
                        save_result(student_id, q_id, "不正解", base_score)

            except Exception as e:
                st.error("❌ 不正解です。（プログラムにエラーがあります）")
                st.warning(f"⚠️ エラー内容: {e}")
                st.info(f"💡 ヒント: {q_data['ヒント']}")
                if not is_solved:
                    save_result(student_id, q_id, "不正解", base_score)

if __name__ == "__main__":
    main()