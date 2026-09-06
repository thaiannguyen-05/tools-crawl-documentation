from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TopicDefinition:
    key: str
    name: str
    description: str
    search_keywords: list[str]
    github_queries: list[str]
    wiki_queries: list[str]
    curated_seeds: dict[str, list[tuple[str, str]]] = field(default_factory=dict)


FAMOUS_TOPICS: dict[str, TopicDefinition] = {
    "ai_tech": TopicDefinition(
        key="ai_tech",
        name="Trí tuệ nhân tạo & Công nghệ thông tin",
        description="Nghiên cứu, ứng dụng AI, machine learning, chuyển đổi số và công nghệ phần mềm",
        search_keywords=[
            "trí tuệ nhân tạo", "học máy machine learning", "học sâu deep learning", "xử lý ngôn ngữ tự nhiên",
            "thị giác máy tính", "mô hình ngôn ngữ lớn LLM", "khoa học dữ liệu data science", "chuyển đổi số việt nam",
            "lập trình python cơ bản nâng cao", "hệ thống cơ sở dữ liệu", "an toàn thông tin an ninh mạng",
            "điện toán đám mây cloud computing", "mạng nơ-ron nhân tạo", "robotics tự động hóa", "blockchain chuỗi khối",
            "phát triển phần mềm công nghệ", "công nghệ viễn thông mạng máy tính", "internet vạn vật iot",
            "phân tích dữ liệu lớn big data", "xử lý tiếng việt nlp", "thuật toán và cấu trúc dữ liệu",
            "kiến trúc hệ thống phần mềm", "phần mềm nguồn mở", "trí tuệ nhân tạo tạo sinh generative ai",
            "khoa học máy tính", "tin học đại cương bài giảng", "hệ điều hành linux windows", "kỹ thuật lập trình web"
        ],
        github_queries=[
            "vietnamese machine learning", "vietnamese nlp ai", "trí tuệ nhân tạo",
            "hoc may deep learning", "vietnamese text classification", "vietnamese data science"
        ],
        wiki_queries=[
            "Trí tuệ nhân tạo", "Học máy", "Xử lý ngôn ngữ tự nhiên", "Thị giác máy tính", "Chuyển đổi số",
            "Học sâu", "Mạng nơ-ron nhân tạo", "Khoa học máy tính", "Dữ liệu lớn", "Khoa học dữ liệu",
            "Điện toán đám mây", "An toàn thông tin", "Internet vạn vật", "Chuỗi khối", "Thị giác máy",
            "Hệ thống thông tin", "Kỹ thuật phần mềm", "Ngôn ngữ lập trình", "Cơ sở dữ liệu", "Robot học"
        ],
        curated_seeds={
            "pdf": [
                ("https://ai.siu.edu.vn/wp-content/uploads/2025/01/Bai-2-HT-1.-SIU.pdf", "Tong_Quan_Ve_Tri_Tue_Nhan_Tao_Va_Phap_Ly"),
                ("http://vjes.vnies.edu.vn/sites/default/files/khdgvn_-_tap_20_-_so_5_-1-11.pdf", "Tac_dong_AI_den_he_thong_giao_duc"),
            ],
            "docx": [
                ("https://sdh.utt.edu.vn/wp-content/uploads/2025/08/ch8gt03_khoa-hoc-du-lieu-va-tri-tue-nhan-tao.docx", "Khoa_hoc_du_lieu_va_tri_tue_nhan_tao"),
            ],
            "doc": [
                ("https://fit.hcmuaf.edu.vn/data/file/Tri%20Tue%20Nhan%20Tao.doc", "De_cuong_chi_tiet_Tri_tue_nhan_tao"),
                ("https://fita.vnua.edu.vn/wp-content/uploads/2013/05/tri-tue-nhan-tao.doc", "Hoc_phan_tri_tue_nhan_tao_VNUA"),
            ],
            "md": [
                ("https://raw.githubusercontent.com/Tkag0001/AI_and_Machine_Learning_for_Coders/main/README.md", "AI_Machine_Learning_for_Coders"),
            ],
        },
    ),
    "economy_finance": TopicDefinition(
        key="economy_finance",
        name="Kinh tế & Tài chính",
        description="Thị trường tài chính, ngân hàng số, chứng khoán, đầu tư và kinh tế vĩ mô",
        search_keywords=[
            "kinh tế tài chính việt nam", "thị trường chứng khoán việt nam", "ngân hàng số fintech",
            "kinh tế vĩ mô tăng trưởng", "quản trị tài chính doanh nghiệp", "chính sách tiền tệ lạm phát",
            "đầu tư tài chính cá nhân", "thương mại quốc tế xuất nhập khẩu", "kế toán kiểm toán doanh nghiệp",
            "thị trường bất động sản kinh tế", "kinh tế vi mô hành vi người tiêu dùng", "quản trị rủi ro tài chính",
            "thuế và chính sách thuế", "kinh tế lượng phân tích số liệu", "khởi nghiệp đổi mới sáng tạo startup",
            "thương mại điện tử thanh toán số", "tài chính công ngân sách nhà nước", "thị trường trái phiếu cổ phiếu",
            "chuỗi cung ứng logistics kinh tế", "quản trị kinh doanh chiến lược", "đầu tư mạo hiểm quỹ đầu tư"
        ],
        github_queries=[
            "vietnamese financial data", "kinh te tai chinh", "vietnam stock market",
            "chung khoan viet nam", "financial dataset vietnam"
        ],
        wiki_queries=[
            "Kinh tế học", "Thị trường chứng khoán", "Kinh tế Việt Nam", "Fintech", "Ngân hàng trung ương",
            "Kinh tế vĩ mô", "Kinh tế vi mô", "Lạm phát", "Chính sách tiền tệ", "Thương mại quốc tế",
            "Đầu tư tài chính", "Cổ phiếu", "Trái phiếu", "Kế toán", "Quản trị kinh doanh",
            "Ngân hàng", "Tiền tệ", "Kinh tế thị trường", "Thị trường vốn", "Tài chính doanh nghiệp"
        ],
        curated_seeds={
            "pdf": [
                ("https://tamlygiaoduc.com.vn/wp-content/uploads/2025/07/86.Nguyen-Thu-Huyen-bai-2-Huong-NV.pdf", "Nghien_cuu_tac_dong_kinh_te_giao_duc"),
            ],
            "docx": [
                ("https://cdn.thuvienphapluat.vn/uploads/Hoidapphapluat/2026/NNL/0203/NghidinhsuaND17.docx", "Nghi_dinh_quan_ly_tai_chinh_doanh_nghiep"),
            ],
            "doc": [
                ("https://cdn.thuvienphapluat.vn/uploads/khoinghiep/2026/04/24/M%E1%BA%ABu%20s%E1%BB%91%2002.doc", "Mau_de_nghi_ho_tro_tai_chinh_khoi_nghiep"),
            ],
            "md": [
                ("https://raw.githubusercontent.com/tiepvupsu/machine_learning_glossary/master/README.md", "Thuat_ngu_kinh_te_va_mo_hinh"),
            ],
        },
    ),
    "health_medicine": TopicDefinition(
        key="health_medicine",
        name="Y tế & Sức khỏe",
        description="Y học, phòng chống dịch bệnh, chăm sóc sức khỏe, dược phẩm và sinh học",
        search_keywords=[
            "y tế sức khỏe cộng đồng", "phòng ngừa bệnh tật dinh dưỡng", "chẩn đoán và điều trị bệnh",
            "chăm sóc sức khỏe ban đầu", "y học lâm sàng dược phẩm", "dịch tễ học bệnh truyền nhiễm",
            "bệnh tim mạch huyết áp", "ung thư và phương pháp điều trị", "sức khỏe tâm thần tâm lý học",
            "nhi khoa và chăm sóc trẻ em", "sản phụ khoa chăm sóc mẹ và bé", "y học cổ truyền thảo dược",
            "chẩn đoán hình ảnh xét nghiệm", "vắc xin và miễn dịch học", "dược lý học độc chất",
            "phẫu thuật ngoại khoa gây mê", "dinh dưỡng học và an toàn thực phẩm", "quản lý bệnh viện y tế số",
            "phục hồi chức năng vật lý trị liệu", "bệnh tiểu đường nội tiết", "chăm sóc người cao tuổi lão khoa"
        ],
        github_queries=[
            "vietnamese medical", "y te suc khoe", "medical dataset vietnam",
            "y hoc lam sang", "suc khoe cong dong"
        ],
        wiki_queries=[
            "Y học", "Sức khỏe cộng đồng", "Dược học", "Hệ thống y tế Việt Nam", "Bệnh truyền nhiễm",
            "Bệnh tim mạch", "Ung thư học", "Miễn dịch học", "Dịch tễ học", "Dinh dưỡng",
            "Vắc-xin", "Sức khỏe tâm thần", "Phẫu thuật", "Bệnh học", "Vi sinh vật học",
            "Thuốc", "Y tế công cộng", "Nội tiết học", "Nhi khoa", "Lão khoa"
        ],
        curated_seeds={
            "pdf": [
                ("https://daihochoabinh.edu.vn/wp-content/uploads/2025/09/12.-ThS.-Do-Ngoc-Diep-TS.-Du-Dinh-Vien-ThS.BS_.-Nguyen-Thi-Thanh-Nhan.pdf", "Ung_dung_cong_nghe_trong_y_te_va_hoc_tap"),
            ],
            "docx": [
                ("https://sdh.utt.edu.vn/wp-content/uploads/2025/08/ch8gt03_khoa-hoc-du-lieu-va-tri-tue-nhan-tao.docx", "Khoa_hoc_du_lieu_trong_y_te"),
            ],
            "doc": [
                ("https://hcmue.edu.vn/images/PhongBan/PhongKHCN/SVNCKH/QD_Quy-dinh-hoat-dong-NCKH-SV_Van-ban.doc", "Quy_dinh_hoat_dong_nghien_cuu_y_sinh"),
            ],
            "md": [
                ("https://raw.githubusercontent.com/giangnguyen2412/InterpretableMLBook-Vietnamese/master/README.md", "Giai_thich_mo_hinh_y_te_va_khoa_hoc"),
            ],
        },
    ),
    "law_governance": TopicDefinition(
        key="law_governance",
        name="Pháp luật & Quản lý",
        description="Văn bản quy phạm pháp luật, chính sách quản lý nhà nước, hành chính và tư pháp",
        search_keywords=[
            "quy định pháp luật việt nam", "văn bản quy phạm pháp luật nghị định", "luật doanh nghiệp và đầu tư",
            "quản lý nhà nước hành chính công", "chính sách an ninh thông tin", "luật dân sự hợp đồng giao dịch",
            "luật hình sự và tố tụng hình sự", "luật đất đai và bất động sản", "luật lao động bảo hiểm xã hội",
            "quyền sở hữu trí tuệ bản quyền", "cải cách hành chính một cửa", "luật thương mại quốc tế wto",
            "tư pháp và thủ tục tòa án", "chính sách công và phát triển", "luật bảo vệ môi trường",
            "quản trị công và phòng chống tham nhũng", "luật cạnh tranh chống độc quyền", "hiến pháp việt nam",
            "nghị quyết chính phủ thủ tướng", "thông tư hướng dẫn thi hành luật", "luật tài chính ngân sách"
        ],
        github_queries=[
            "luat viet nam", "van ban phap luat", "vietnamese legal documents",
            "vietnam legal text", "chinh sach phap luat"
        ],
        wiki_queries=[
            "Pháp luật Việt Nam", "Văn bản quy phạm pháp luật", "Hành chính công", "Luật Dân sự", "Hiến pháp",
            "Luật Hình sự", "Luật Doanh nghiệp", "Luật Lao động", "Luật Đất đai", "Sở hữu trí tuệ",
            "Tư pháp", "Tòa án nhân dân", "Chính phủ Việt Nam", "Chính sách công", "Nhà nước pháp quyền",
            "Luật Thương mại", "Cải cách hành chính", "Quyền công dân", "Pháp lệnh", "Nghị định"
        ],
        curated_seeds={
            "pdf": [
                ("https://www.dost.hochiminhcity.gov.vn/documents/1165/Ai_for_Student_Phien_ban_Tieng_Viet_SIHUB.pdf", "Chinh_sach_phap_ly_khoa_hoc_cong_nghe_TPHCM"),
            ],
            "docx": [
                ("https://cdn.thuvienphapluat.vn/uploads/Hoidapphapluat/2026/NNL/0203/NghidinhsuaND17.docx", "Nghi_dinh_quy_pham_phap_luat_chinh_phu"),
            ],
            "doc": [
                ("https://files.thuvienphapluat.vn/uploads/hopdong/MAU%20AI03a-142-2026-ND-CP.doc", "Mau_van_ban_phap_luat_nghi_dinh_CP"),
            ],
            "md": [
                ("https://raw.githubusercontent.com/undertheseanlp/underthesea/main/README.md", "Tai_lieu_ngon_ngu_va_phap_ly"),
            ],
        },
    ),
    "education_environment": TopicDefinition(
        key="education_environment",
        name="Giáo dục & Môi trường",
        description="Đổi mới giáo dục, phương pháp sư phạm, biến đổi khí hậu và bảo vệ môi trường",
        search_keywords=[
            "đổi mới phương pháp giáo dục", "nghiên cứu khoa học sư phạm", "biến đổi khí hậu việt nam",
            "bảo vệ môi trường sinh thái", "quản lý tài nguyên môi trường", "giáo dục đại học và cao đẳng",
            "công nghệ giáo dục edtech", "phương pháp giảng dạy tích cực", "năng lượng tái tạo điện mặt trời",
            "quản lý chất thải và rác thải", "ô nhiễm không khí và nguồn nước", "phát triển bền vững esg",
            "tâm lý học giáo dục học đường", "chương trình giáo dục phổ thông mới", "bảo tồn đa dạng sinh học",
            "kinh tế tuần hoàn tài nguyên xanh", "giáo dục kỹ năng sống", "đánh giá và kiểm định chất lượng giáo dục",
            "quản lý rừng và đất ngập nước", "khí hậu nhiệt đới gió mùa việt nam", "giảm phát thải khí nhà kính net zero"
        ],
        github_queries=[
            "vietnamese education", "moi truong bien doi khi hau", "giao duc moi truong",
            "vietnam education dataset", "tai nguyen moi truong"
        ],
        wiki_queries=[
            "Giáo dục Việt Nam", "Biến đổi khí hậu", "Bảo vệ môi trường", "Năng lượng tái tạo", "Phát triển bền vững",
            "Sinh thái học", "Giáo dục đại học", "Sư phạm", "Tài nguyên thiên nhiên", "Đa dạng sinh học",
            "Kinh tế tuần hoàn", "Ô nhiễm môi trường", "Rừng ngập mặn", "Khí tượng học", "Thủy văn học",
            "Năng lượng mặt trời", "Năng lượng gió", "Hiệu ứng nhà kính", "Công nghệ giáo dục", "Tâm lý học giáo dục"
        ],
        curated_seeds={
            "pdf": [
                ("https://daotao.neu.edu.vn/Resources/Docs/SubDomain/daotao/CDR/10-TS-NguyenDangKhoa-NguyenQuocHung.pdf", "Phat_trien_giao_duc_dai_hoc_va_moi_truong"),
            ],
            "docx": [
                ("https://sdh.utt.edu.vn/wp-content/uploads/2025/08/ch8gt03_khoa-hoc-du-lieu-va-tri-tue-nhan-tao.docx", "Chuong_trinh_dao_tao_giao_duc_cong_nghe"),
            ],
            "doc": [
                ("https://www.utc.edu.vn/upload/files/7_%20K%E1%BB%B8%20THU%E1%BA%ACT%20ROBOT%20V%C3%80%20TR%C3%8D%20T%E1%BB%A4E%20NH%C3%82N%20T%E1%BA%A0O.doc", "Chuong_trinh_khung_dao_tao_UTC"),
            ],
            "md": [
                ("https://raw.githubusercontent.com/vunb/awesome-vietnamese-nlp/master/README.md", "Tai_nguyen_giao_duc_khoa_hoc_viet_nam"),
            ],
        },
    ),
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_DOWNLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50MB per file
SUPPORTED_FORMATS = ["pdf", "docx", "doc", "txt", "md"]
