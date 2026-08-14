import streamlit as st
import pandas as pd
import io
import contextlib
from datetime import datetime
import os
import requests 

# 先生が発行したGASのウェブアプリURLをここに貼り付けてください
GAS_URL = "https://script.google.com/macros/s/AKfycbx2tVGq9CWtpwoxH8sQPT6jgNZTCLAaEN5Xgl_uNvpn26prn3sl77QLZusqzh5GmEa1/exec"

# 先生用画面に入るためのパスワード（好きな文字や数字に変更してください）
ADMIN_PASSWORD = "1234"

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

def load_data():
    """問題データの読み込み（CSVファイルから）"""
    try:
        df = pd.read_csv("questions.csv", encoding="shift_jis")
        df = df.fillna("")
        return df
    except FileNotFoundError:
        st.error("エラー: 'questions.csv' というファイルが見つかりません。")
        st.stop()

def main():
    st.sidebar.title("⚙️ メニュー")
    mode = st.sidebar.radio("モード選択", ["生徒用（学習画面）", "先生用（集計画面）"])

    # --- 先生用画面 ---
    if mode == "先生用（集計画面）":
        st.title("📊 学習履歴の集計（先生用）")
        
        # パスワード入力欄を追加（type="password" で伏せ字になります）
        password_input = st.text_input("🔑 パスワードを入力してください", type="password")
        
        # パスワードが間違っている、または未入力の場合はここで処理をストップ
        if password_input != ADMIN_PASSWORD:
            if password_input != "":
                st.error("パスワードが違います。")
            return 
            
        # --- ここから下はパスワード正解時のみ表示される ---
        st.success("認証に成功しました。")

        # 生徒画面にあった「問題データ確認」を先生画面に移動
        df = load_data()
        with st.expander("👀 読み込まれている問題データを確認する"): 
            st.dataframe(df[["問題ID", "問題種別", "問題文"]], hide_index=False) 
        
        st.markdown("### 📝 生徒の解答履歴")
        try:
            response = requests.get(GAS_URL)
            data = response.json()
            if len(data) > 1:
                df_results = pd.DataFrame(data[1:], columns=data[0])
                st.dataframe(df_results, use_container_width=True)
            else:
                st.warning("まだ解答データがありません。")
        except Exception as e:
            st.error(f"データの読み込みに失敗しました。URLを確認してください。")
        return 

    # --- 生徒用画面 ---
    st.markdown("## 🐍 Pythonプログラミング学習") 
    
    student_id = st.sidebar.text_input("👤 学籍番号を入力してください（半角数字）")
    if not student_id:
        st.warning("👈 左のメニューに学籍番号を入力すると問題が始まります！")
        st.stop()  # 🛑 未入力ならここでストップ！
        
    if not student_id.isascii():
        st.error("⚠️ 学籍番号に「全角文字」が含まれています。半角数字に直してください。")
        st.stop()  # 🛑 全角ならここでストップ！

    # ↓ここから下は、半角数字が正しく入力された時だけ実行されます
    st.write(f"こんにちは、{student_id} さん！")
    
    # データ読み込み
    df = load_data()

    # 問題を選択
    q_id = st.selectbox("📝 挑戦する問題を選んでください", df["問題ID"].tolist())
    q_data = df[df["問題ID"] == q_id].iloc[0]

    # 🌟🌟🌟 ここで全問題共通で「配点」をCSVから読み込む 🌟🌟🌟
    base_score = 10  # CSVが空欄だった場合の予備
    if "配点" in q_data and pd.notna(q_data["配点"]):
        try:
            # 文字列にして前後の余計なスペースを消してから数字に変換（全角数字も対応）
            base_score = int(str(q_data["配点"]).strip())
        except:
            pass

    st.write(q_data['問題文'])

    # ==============================
    # 1. 選択問題の場合
    # ==============================
    if q_data['問題種別'] == '選択':
        options = [opt.strip() for opt in str(q_data['選択肢']).split(',')]
        user_choice = st.radio("選択してください:", options)
        
        if st.button("解答する", type="primary"):
            if user_choice == str(q_data['正解']).strip():
                st.success("🎉 大正解！")
                st.balloons()
                # さきほど読み込んだ base_score を送信
                save_result(student_id, q_id, "正解", base_score)
            else:
                st.error("❌ 不正解...もう一度考えてみよう！")
                st.info(f"💡 ヒント: {q_data['ヒント']}")
                save_result(student_id, q_id, "不正解", base_score)

    # ==============================
    # 2. コード記述問題の場合
    # ==============================
    elif q_data['問題種別'] == 'コード':
        user_code = st.text_area("Pythonコードを入力:", height=150)
        
        if st.button("▶️ コードを実行して解答する", type="primary"):
            if not user_code:
                st.warning("コードが入力されていません。")
                return

            # --- キーワードチェック ---
            if "必須キーワード" in q_data and pd.notna(q_data["必須キーワード"]):
                required_words = [w.strip() for w in str(q_data["必須キーワード"]).split(",")]
                missing_words = [w for w in required_words if w not in user_code]
                
                if missing_words:
                    st.error(f"❌ 不正解です。指定されたキーワード（{', '.join(missing_words)}）がコードに含まれていません。")
                    st.info(f"💡 ヒント: {q_data['ヒント']}")
                    save_result(student_id, q_id, "不正解", base_score)
                    return

            f = io.StringIO()
            try:
                with contextlib.redirect_stdout(f):
                    exec(user_code, {})
                output = f.getvalue()

                # 結果の判定
                correct_answer = str(q_data['正解']).strip()
                if output.strip() == correct_answer:
                    st.success("🎉 大正解！")
                    st.balloons()
                    save_result(student_id, q_id, "正解", base_score)
                else:
                    st.error("❌ 不正解です。")
                    st.code(output, language="text")
                    st.info(f"💡 ヒント: {q_data['ヒント']}")
                    save_result(student_id, q_id, "不正解", base_score)

            except Exception as e:
                st.error("❌ 不正解です。（プログラムにエラーがあります）")
                st.warning(f"⚠️ エラー内容: {e}")
                st.info(f"💡 ヒント: {q_data['ヒント']}")
                save_result(student_id, q_id, "不正解", base_score)

if __name__ == "__main__":
    main()