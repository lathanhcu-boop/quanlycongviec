import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="QUẢN LÝ NHÂN SỰ", layout="wide")

URL_NV = "https://docs.google.com/spreadsheets/d/1XoiaAab4uTuHiGw5Q54JF362P--QjQsA/export?format=csv&gid=1095724926"
URL_CV = "https://docs.google.com/spreadsheets/d/1YpMjVzZLsfX9Eedu3rrlDlKiVCHQcNidJK69Pw1wxUo/export?format=csv&gid=2113008419"

DATA_FILE = "lich_su_lam_viec.csv"
ASSIGN_HISTORY_FILE = "phan_cong_data.csv"
ISSUE_FILE = "cong_viec_phat_sinh.csv" # File lưu yêu cầu từ khách hàng

@st.cache_data(ttl=60)
def load_data():
    try:
        df_nv = pd.read_csv(URL_NV)
        df_nv.columns = df_nv.columns.str.strip()
        df_cv = pd.read_csv(URL_CV)
        df_cv.columns = df_cv.columns.str.strip()
        job_dict = df_cv.groupby('KhuVuc')['CongViec'].apply(list).to_dict()
        return df_nv, job_dict
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu từ Google Sheets: {e}")
        return pd.DataFrame(), {}

df_nv, job_list = load_data()
today_str = date.today().strftime("%Y-%m-%d")

# --- 2. KHỞI TẠO FILE & SESSION STATE ---
def init_files():
    if not os.path.exists(ASSIGN_HISTORY_FILE):
        pd.DataFrame(columns=["Ngày", "Nhân viên", "Khu vực"]).to_csv(ASSIGN_HISTORY_FILE, index=False, encoding='utf-8-sig')
    if not os.path.exists(ISSUE_FILE):
        pd.DataFrame(columns=["Ngày", "Khu vực", "Nội dung", "Khách hàng", "Trạng thái"]).to_csv(ISSUE_FILE, index=False, encoding='utf-8-sig')
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if 'Ngày' not in df.columns: df['Ngày'] = today_str
        st.session_state.history = df
    else:
        st.session_state.history = pd.DataFrame(columns=["Ngày", "Khu vực", "Công việc", "Nhân viên", "Bắt đầu", "Hoàn thành", "Trạng thái", "Xác nhận", "Thời gian QC"])

init_files()

if 'user' not in st.session_state: st.session_state.user = None
if 'role' not in st.session_state: st.session_state.role = None

# --- 3. GIAO DIỆN ĐĂNG NHẬP ---
if st.session_state.user is None:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("#### HỆ THỐNG QUẢN LÝ CHẤT LƯỢNG")
    st.markdown("</div>", unsafe_allow_html=True)
    
    with st.container(border=True):
        role_select = st.radio("Đăng nhập với vai trò:", ["Nhân viên", "Giám sát", "Khách hàng"], horizontal=True)
        
        if role_select == "Nhân viên":
            uid = st.text_input("Nhập mã nhân viên:").strip()
            if st.button("Đăng nhập", use_container_width=True):
                match = df_nv[df_nv['MaNV'].astype(str) == uid]
                if not match.empty:
                    st.session_state.user = match.iloc[0]['HoTen']
                    st.session_state.role = "staff"; st.rerun()
                else: st.error("Mã nhân viên không đúng!")
                
        elif role_select == "Khách hàng":
            cus_name = st.text_input("Nhập tên khách hàng / Số phòng:").strip()
            if st.button("Truy cập hệ thống", use_container_width=True):
                if cus_name:
                    st.session_state.user = cus_name
                    st.session_state.role = "customer"; st.rerun()
                else: st.warning("Vui lòng nhập tên hoặc số phòng!")
                
        else:
            email = st.text_input("Email Quản lý:").strip().lower()
            if st.button("Đăng nhập Admin", use_container_width=True):
                st.session_state.user = "Admin"; st.session_state.role = "admin"; st.rerun()

# --- 4. GIAO DIỆN CHÍNH ---
else:
    st.sidebar.markdown(f"👤: **{st.session_state.user}**")
    st.sidebar.markdown(f"Vai trò: `{st.session_state.role.upper()}`")
    if st.sidebar.button("Đăng xuất"):
        st.session_state.user = None; st.rerun()

    # ========================== GIAO DIỆN KHÁCH HÀNG ==========================
    if st.session_state.role == "customer":
        st.header(f"Chào mừng Quý khách {st.session_state.user}")
        t_request, t_history = st.tabs(["🆕 Gửi yêu cầu phát sinh", "📜 Theo dõi tiến độ & Lịch sử"])
        
        with t_request:
            st.subheader("Báo cáo công việc phát sinh")
            with st.form("customer_request"):
                kv_req = st.selectbox("📍 Khu vực cần xử lý:", list(job_list.keys()))
                content_req = st.text_area("📝 Nội dung yêu cầu (Ví dụ: Đèn hỏng, Tràn nước, Cần vệ sinh gấp...):")
                if st.form_submit_button("Gửi yêu cầu cho Ban quản lý"):
                    if content_req:
                        new_issue = pd.DataFrame([{
                            "Ngày": today_str, "Khu vực": kv_req, "Nội dung": content_req, 
                            "Khách hàng": st.session_state.user, "Trạng thái": "Chờ xử lý"
                        }])
                        new_issue.to_csv(ISSUE_FILE, mode='a', header=not os.path.exists(ISSUE_FILE), index=False, encoding='utf-8-sig')
                        st.success("Yêu cầu đã được gửi! Ban quản lý sẽ sớm phân công nhân sự.")
                    else: st.warning("Vui lòng nhập nội dung!")

        with t_history:
            st.subheader("Lịch sử vận hành & Nghiệm thu")
            df_hist = st.session_state.history.copy()
            # Khách hàng xem lịch sử của khu vực liên quan hoặc tất cả (tùy cấu hình, ở đây cho xem tất cả lịch sử đã xong)
            df_cus_view = df_hist[df_hist['Trạng thái'] == "Hoàn thành"].sort_values(by="Ngày", ascending=False)
            st.dataframe(df_cus_view, use_container_width=True, hide_index=True)

    # ========================== GIAO DIỆN QUẢN LÝ (ADMIN) ==========================
    elif st.session_state.role == "admin":
        t_real, t_issue, t_mgmt, t_report = st.tabs(["📡 Real-time", "🚨 Yêu cầu từ Khách", "👥 Phân công", "📊 Nghiệm thu"])
        
        with t_real:
            df_now = st.session_state.history[(st.session_state.history['Trạng thái'] == "Đang làm") & (st.session_state.history['Ngày'] == today_str)]
            st.dataframe(df_now.drop(columns=['Xác nhận', 'Thời gian QC', 'Ngày'], errors='ignore'), use_container_width=True)

        with t_issue:
            st.subheader("Danh sách yêu cầu phát sinh từ khách hàng")
            if os.path.exists(ISSUE_FILE):
                df_issues = pd.read_csv(ISSUE_FILE)
                df_pending = df_issues[df_issues['Trạng thái'] == "Chờ xử lý"]
                if not df_pending.empty:
                    st.write(f"Có **{len(df_pending)}** yêu cầu mới chưa phân công.")
                    st.dataframe(df_pending, use_container_width=True)
                    st.info("💡 Hãy sang tab 'Phân công' để điều phối nhân viên xử lý các mục này.")
                else: st.success("Không có yêu cầu phát sinh nào đang chờ.")
            else: st.info("Chưa có dữ liệu yêu cầu.")

        with t_mgmt:
            col_a, col_b = st.columns([1, 1.2])
            with col_a:
                st.subheader("🆕 Giao việc")
                # Thêm lựa chọn lấy việc từ danh sách phát sinh
                source = st.radio("Nguồn công việc:", ["Từ danh mục chuẩn", "Từ yêu cầu Khách hàng"], horizontal=True)
                
                with st.form("assign_form"):
                    w_date = st.date_input("Ngày làm việc:", date.today())
                    if source == "Từ danh mục chuẩn":
                        sel_kv = st.selectbox("📍 Khu vực:", list(job_list.keys()))
                        sel_job_name = "Theo checklist chuẩn"
                    else:
                        df_issues = pd.read_csv(ISSUE_FILE)
                        df_pending = df_issues[df_issues['Trạng thái'] == "Chờ xử lý"]
                        if not df_pending.empty:
                            selected_issue_idx = st.selectbox("Chọn yêu cầu:", df_pending.index, format_func=lambda x: f"{df_pending.loc[x, 'Khu vực']}: {df_pending.loc[x, 'Nội dung']}")
                            sel_kv = df_pending.loc[selected_issue_idx, 'Khu vực']
                            sel_job_name = f"PHÁT SINH: {df_pending.loc[selected_issue_idx, 'Nội dung']}"
                        else:
                            st.warning("Không có yêu cầu phát sinh.")
                            sel_kv = None
                    
                    sel_nvs = st.multiselect("👥 Nhân viên thực hiện:", df_nv['HoTen'].tolist())
                    
                    if st.form_submit_button("Xác nhận phân công"):
                        if sel_nvs and sel_kv:
                            # Lưu vào phân công chính
                            new_assign = pd.DataFrame({"Ngày": [w_date.strftime("%Y-%m-%d")] * len(sel_nvs), "Nhân viên": sel_nvs, "Khu vực": [f"{sel_kv} ({sel_job_name})"] * len(sel_nvs)})
                            new_assign.to_csv(ASSIGN_HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
                            
                            # Nếu là việc phát sinh, cập nhật trạng thái trong file Issue
                            if source == "Từ yêu cầu Khách hàng":
                                df_issues = pd.read_csv(ISSUE_FILE)
                                df_issues.loc[selected_issue_idx, 'Trạng thái'] = "Đã phân công"
                                df_issues.to_csv(ISSUE_FILE, index=False, encoding='utf-8-sig')
                            
                            st.success("Đã phân công xong!"); st.rerun()

            with col_b:
                st.subheader("🔍 Lịch trực")
                s_date = st.date_input("Xem ngày:", date.today())
                df_v = pd.read_csv(ASSIGN_HISTORY_FILE)
                st.dataframe(df_v[df_v['Ngày'] == s_date.strftime("%Y-%m-%d")][['Nhân viên', 'Khu vực']], use_container_width=True)

        with t_report:
            report_date = st.date_input("Ngày nghiệm thu:", date.today())
            rep_str = report_date.strftime("%Y-%m-%d")
            df_full = st.session_state.history.copy()
            df_full['Xác nhận'] = df_full['Xác nhận'].map({True: True, False: False, 'True': True, 'False': False, 1: True, 0: False}).fillna(False).astype(bool)
            
            df_day = df_full[df_full['Ngày'] == rep_str]
            df_cho = df_day[df_day['Xác nhận'] == False]
            df_xong = df_day[df_day['Xác nhận'] == True]

            st.markdown("#### ⏳ Chờ nghiệm thu")
            if not df_cho.empty:
                edited = st.data_editor(df_cho, column_config={"Xác nhận": st.column_config.CheckboxColumn("Đạt QC")}, disabled=["Ngày","Khu vực","Công việc","Nhân viên","Bắt đầu","Hoàn thành","Trạng thái","Thời gian QC"], use_container_width=True, hide_index=True)
                if st.button("💾 Lưu và Khóa kết quả"):
                    now_qc = datetime.now().strftime("%H:%M:%S %d/%m")
                    for idx in edited.index:
                        if edited.at[idx, 'Xác nhận'] == True:
                            st.session_state.history.at[idx, 'Xác nhận'] = True
                            st.session_state.history.at[idx, 'Thời gian QC'] = now_qc
                    st.session_state.history.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
                    st.rerun()
            st.markdown("#### 🔒 Đã khóa")
            st.dataframe(df_xong, use_container_width=True, hide_index=True)

    # ========================== GIAO DIỆN NHÂN VIÊN ==========================
    else:
        st.header(f"📋 Nhiệm vụ ngày {datetime.now().strftime('%d/%m/%Y')}")
        df_assign = pd.read_csv(ASSIGN_HISTORY_FILE)
        my_assign = df_assign[(df_assign['Nhân viên'] == st.session_state.user) & (df_assign['Ngày'] == today_str)]
        
        if my_assign.empty:
            st.warning("Bạn chưa có lịch phân công. Vui lòng kiểm tra với Quản lý.")
            area_selected = st.selectbox("Xem khu vực:", list(job_list.keys()))
            jobs_to_show = job_list[area_selected]
        else:
            # Lấy khu vực được phân công
            area_selected = my_assign.iloc[-1]['Khu vực']

            st.success(f"📍 Khu vực trực: **{area_selected}**")

            # Tách khu vực gốc
            area_base = area_selected.split(" (")[0]

            # Nếu là công việc phát sinh
            if "PHÁT SINH:" in area_selected:
                jobs_to_show = [
                    area_selected.split("PHÁT SINH: ")[1].replace(")", "")
                ]
            else:
                # Hiển thị checklist chuẩn
                jobs_to_show = job_list.get(area_base, [])
            
        st.divider()
        for i, job in enumerate(jobs_to_show):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1.5, 1])
                c1.write(f"🔹 **{job}**")
                
                mask = (st.session_state.history['Ngày'] == today_str) & (st.session_state.history['Công việc'] == job) & (st.session_state.history['Nhân viên'] == st.session_state.user)
                status_job = st.session_state.history[mask]

                if not status_job.empty and (status_job['Trạng thái'] == "Đang làm").any():
                    c2.info(f"⏳ Bắt đầu: {status_job.iloc[-1]['Bắt đầu']}")
                    if c3.button("✅ Xong", key=f"e_{i}"):
                        idx = status_job.index[-1]
                        st.session_state.history.at[idx, 'Hoàn thành'] = datetime.now().strftime("%H:%M:%S")
                        st.session_state.history.at[idx, 'Trạng thái'] = "Hoàn thành"
                        st.session_state.history.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
                        st.rerun()
                elif not status_job.empty and (status_job['Trạng thái'] == "Hoàn thành").any():
                    last = status_job.iloc[-1]
                    c2.success(f"Xong: {last['Hoàn thành']}")
                    if last['Xác nhận'] == True: st.caption(f"⭐ QC Đạt: {last['Thời gian QC']}")
                else:
                    if c2.button("🚀 Bắt đầu", key=f"s_{i}"):
                        new_row = {"Ngày": today_str, "Khu vực": area_selected, "Công việc": job, "Nhân viên": st.session_state.user, "Bắt đầu": datetime.now().strftime("%H:%M:%S"), "Hoàn thành": "-", "Trạng thái": "Đang làm", "Xác nhận": False, "Thời gian QC": "-"}
                        st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([new_row])], ignore_index=True)
                        st.session_state.history.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
                        st.rerun()
