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
        description="Nghiên cứu, ứng dụng AI, machine learning, chuyển đổi số và công nghệ",
        search_keywords=[
            "trí tuệ nhân tạo",
            "học máy machine learning",
            "chuyển đổi số việt nam",
            "thị giác máy tính",
            "xử lý ngôn ngữ tự nhiên tiếng việt",
        ],
        github_queries=["vietnamese machine learning", "vietnamese nlp ai", "trí tuệ nhân tạo"],
        wiki_queries=["Trí tuệ nhân tạo", "Học máy", "Xử lý ngôn ngữ tự nhiên", "Thị giác máy tính", "Chuyển đổi số"],
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
        description="Thị trường tài chính, chứng khoán, ngân hàng số và kinh tế học",
        search_keywords=[
            "kinh tế tài chính việt nam",
            "thị trường chứng khoán việt nam",
            "ngân hàng số fintech",
            "kinh tế vĩ mô tăng trưởng",
            "quản trị tài chính doanh nghiệp",
        ],
        github_queries=["vietnamese financial data", "kinh te tai chinh"],
        wiki_queries=["Kinh tế học", "Thị trường chứng khoán", "Kinh tế Việt Nam", "Fintech", "Ngân hàng trung ương"],
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
        description="Y học, phòng chống dịch bệnh, chăm sóc sức khỏe và dược học",
        search_keywords=[
            "y tế sức khỏe cộng đồng",
            "phòng ngừa bệnh tật dinh dưỡng",
            "chẩn đoán và điều trị bệnh",
            "chăm sóc sức khỏe ban đầu",
            "y học lâm sàng dược phẩm",
        ],
        github_queries=["vietnamese medical", "y te suc khoe"],
        wiki_queries=["Y học", "Sức khỏe cộng đồng", "Dược học", "Hệ thống y tế Việt Nam", "Bệnh truyền nhiễm"],
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
        description="Văn bản quy phạm pháp luật, chính sách quản lý nhà nước và thủ tục hành chính",
        search_keywords=[
            "quy định pháp luật việt nam",
            "văn bản quy phạm pháp luật nghị định",
            "luật doanh nghiệp và đầu tư",
            "quản lý nhà nước hành chính",
            "chính sách an ninh thông tin",
        ],
        github_queries=["luat viet nam", "van ban phap luat"],
        wiki_queries=["Pháp luật Việt Nam", "Văn bản quy phạm pháp luật", "Hành chính công", "Luật Dân sự", "Hiến pháp"],
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
        description="Đổi mới giáo dục, phương pháp sư phạm, biến đổi khí hậu và môi trường",
        search_keywords=[
            "đổi mới phương pháp giáo dục",
            "nghiên cứu khoa học sư phạm",
            "biến đổi khí hậu việt nam",
            "bảo vệ môi trường sinh thái",
            "quản lý tài nguyên môi trường",
        ],
        github_queries=["vietnamese education", "moi truong bien doi khi hau"],
        wiki_queries=["Giáo dục Việt Nam", "Biến đổi khí hậu", "Bảo vệ môi trường", "Năng lượng tái tạo", "Phát triển bền vững"],
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
