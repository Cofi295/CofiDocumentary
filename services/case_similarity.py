"""
Multilingual Case, Entity, Phonetic Alias, and Semantic Similarity Engine for CofiDocumentary.
Detects duplicate documentary topics and true crime / investigative / infrastructure cases across
Korean (both Sino-Korean 한자음 and Mandarin 원음 transcriptions), Vietnamese, Chinese, and English.
"""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Any

_VN_UPPER = "A-ZĐÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"
_VN_LOWER = "a-zđàáảãạăằắẳẵặâầấẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ"
_VN_PROPER_NOUN_RE = re.compile(
    rf"([{_VN_UPPER}][{_VN_LOWER}]+(?:\s+[{_VN_UPPER}][{_VN_LOWER}]+){{1,3}})"
)

_PREFIX_CLEAN_RE = re.compile(
    "|".join(
        (
            r"\[중국\s*실화\s*사건\]",
            r"\[중국\s*첨단사기\s*실화\s*사건\]",
            r"\[중국\s*사기\s*실화\]",
            r"\[중국\s*금융\s*실화\s*사건\]",
            r"\[중국\s*인프라의\s*이면\]",
            r"\[중국\]",
            r"\[하나님의\s*말씀\]",
            r"\[vụ\s*án\s*có\s*thật\s*ở\s*trung\s*quốc\]",
            r"\[vụ\s*án\s*tài\s*chính\s*có\s*thật\s*ở\s*trung\s*quốc\]",
            r"\[vụ\s*lừa\s*đảo\s*có\s*thật\s*ở\s*trung\s*quốc\]",
            r"\[mặt\s*tối\s*hạ\s*tầng\s*trung\s*quốc\]",
            r"\[lời\s*chúa\s*mỗi\s*ngày\]",
            r"\[declassified\s*us\s*intelligence\s*files\]",
            r"\[presidential\s*records\s*&\s*executive\s*forensics\]",
        )
    ),
    re.IGNORECASE,
)
_THOUSANDS_COMMA_RE = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_PUNCT_CLEAN_RE = re.compile(r"[\(\)\[\]\{\}\<\>\"\'`«»\—\–\-·|:/\\,.?!;~@#$%^&*+=_\n\r\t]+")


@lru_cache(maxsize=16384)
def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = _PREFIX_CLEAN_RE.sub(" ", text)
    cleaned = text.lower()
    # Remove thousands commas inside numbers so 9,150만 / 3,000미터 / 5,100만 normalize identically
    cleaned = _THOUSANDS_COMMA_RE.sub("", cleaned)
    # Normalize punctuation and brackets
    cleaned = _PUNCT_CLEAN_RE.sub(" ", cleaned)
    return " ".join(cleaned.split())


GENERIC_HANZI_STOPWORDS: set[str] = {
    "中国", "特大", "真实", "案件", "真实案件", "大案", "纪实", "侦破", "告破", "警方",
    "公安", "公安部", "通缉", "通缉令", "潜逃", "落网", "追逃", "猎狐", "猎狐行动",
    "今日说法", "天网", "一线", "庭审", "庭审现场", "法院", "中级人民法院", "人民检察院",
    "银行", "证券", "金库", "金融", "挪用公款", "非法集资", "诈骗", "贪污", "受贿",
    "悬案", "命案", "积案", "命案积案", "杀人", "连环", "失踪", "死刑", "无期徒刑",
    "年侦破", "年侦破案", "侦破纪实", "潜逃案", "特大案件", "真实大案", "贪污挪用", "挪用",
    "特大持枪", "系列抢劫", "持枪抢劫", "抢劫案", "银行劫案", "运钞车", "运钞车劫案",
    "越狱", "越狱案", "大追捕", "追捕", "追捕案", "围捕", "围捕案", "专案", "系列案",
    "亿元", "万元", "亿美元", "现金", "被盗", "被盗案", "买彩票", "票据", "支行", "分行",
    "中国银行", "农业银行", "工商银行", "建设银行", "合作银行", "村镇银行", "储蓄所",
    "主犯", "嫌犯", "逃犯", "重案", "命案逃犯", "通缉犯", "级通缉", "级通缉令", "级通缉犯",
    "变身", "伪装", "伪装案", "洗白", "洗白身份", "隐姓埋名", "亿万富豪", "富商", "董事长",
    "指纹", "家系", "家系侦破", "物证", "微量物证", "弹道", "爆炸", "勒索", "自首",
    # Province & major city names (sharing a city/province alone does NOT make two cases identical)
    "北京", "上海", "天津", "重庆", "广东", "广州", "深圳", "浙江", "杭州", "宁波", "温州", "绍兴",
    "江苏", "南京", "无锡", "苏州", "常州", "河南", "郑州", "洛阳", "周口", "安阳", "驻马店",
    "河北", "石家庄", "邯郸", "衡水", "山东", "济南", "青岛", "泰安", "山西", "太原", "运城", "闻喜",
    "陕西", "西安", "四川", "成都", "宜宾", "湖北", "武汉", "潜江", "咸宁", "湖南", "长沙", "常德", "怀化", "衡阳",
    "江西", "南昌", "赣州", "鄱阳", "安徽", "合肥", "宿州", "蚌埠", "凤阳", "福建", "福州", "厦门", "三明", "福安",
    "广西", "南宁", "桂林", "北海", "岑溪", "柳州", "云南", "昆明", "贵州", "贵阳", "凯里",
    "辽宁", "沈阳", "大连", "营口", "锦州", "吉林", "长春", "通化", "黑龙江", "哈尔滨", "大庆", "肇东",
    "内蒙古", "呼和浩特", "宁夏", "银川", "甘肃", "兰州", "白银", "青海", "西宁", "新疆", "乌鲁木齐", "海南", "三亚",
    "河南郑州", "浙江杭州", "浙江宁波", "浙江温州", "江苏南京", "湖北武汉", "辽宁沈阳", "陕西西安",
    "黑龙江大庆", "黑龙江哈尔滨", "内蒙古呼和浩特", "广东深圳", "广东广州", "四川成都", "湖南常德", "湖南长沙",
    "广西桂林", "云南昆明", "福建厦门", "河北石家庄", "河北邯郸", "山东青岛", "山西闻喜", "安徽宿州",
}

GENERIC_STOPWORDS: set[str] = {
    "중국", "중국의", "실화", "사건", "실화사건", "미제사건", "미제사건의", "수배범", "수배범이",
    "수배범의", "용의자", "진범", "진범이", "범인이", "형사들", "형사들의", "수사관", "공안",
    "동안", "전말", "이유", "사연", "진실", "진실을", "사라진", "숨겨진", "남겨진", "밝혀진",
    "트루크라임", "특급수배록", "역사상", "최대", "최악의", "살아온", "행세한", "위장해",
    "변신한", "숨어", "지낸", "사건의", "범인의", "남자의", "여인의", "마을에서", "중대",
    "수배", "추적", "파일", "검거", "도주", "잠적", "비밀", "미스터리", "사라졌다", "남기고",
    "증발한", "하나에", "도망쳤다", "지갑의", "다단계", "사기", "금융", "첨단", "실체",
    "평생", "모은", "퇴직금을", "퇴직금", "넣자", "벌어진", "노후", "자금", "이자에", "땅속",
    "묻힌", "장부", "범인은", "바로", "동네", "모범", "시민이었다", "우등생은", "도주했나",
    "프로파일링", "무너지게", "한마디", "수사", "기록의", "알리바이를", "설계한", "소름", "돋는",
    "수송차", "수송차를", "현금수송차", "세탁한", "역추적", "도주극", "도피극", "증권사", "증권사를",
    "경찰서", "경찰서에", "사법부를", "뒤흔든", "이름으로", "억만장자", "가장으로", "산속만", "산속을",
    "운전수", "교도소", "추격전", "대추격", "포위망", "포위망을", "검문소를", "감옥을", "주범의",
    "수감자", "수감자의", "사업가", "재벌로", "회장이", "지점장", "은행장", "금고에서", "빼돌려",
    "빼돌린", "사라져", "숨어든", "붙잡힌", "정체", "얼굴", "결말", "최후", "진실과", "운동장",
    "고찰의", "스님으로", "연구원", "연구원으로", "정찰병", "공안부", "수배령", "단서", "지문",
    "생명을", "생명", "앗아간", "앗아가고", "앗아가며", "운명을", "목숨을", "사람의", "사람을", "청춘의",
    "교도관", "교도관의", "당직", "수감자들", "경비원", "경비원의", "연쇄", "특급", "강력사건", "미제",
    "지명수배범", "현장에", "현장에서", "찾아낸", "무너뜨린", "드러난", "지목한", "습격해", "습격한",
    "빠져나간", "가리킨", "멈춰", "세운", "뒤져", "걸어", "나간", "숨어산", "살아온", "통과한",
    "trung quốc", "vụ án", "vụ án có thật", "kỳ án", "đại án", "chuyên án", "hồ sơ",
    "tội phạm", "truy nã", "cảnh sát", "hình sự", "pháp y", "sự thật", "bí ẩn", "toàn cảnh",
    "nghi phạm", "hung thủ", "nhà văn", "triệu phú", "tử tù", "xanh tiền", "màn kịch",
    "lừa đảo", "công nghệ cao", "tài chính", "tiền ảo", "dòng tiền", "truy vết",
    "vụ lừa đảo có", "vụ án có", "thật ở trung quốc", "mặt tối hạ tầng", "lời chúa mỗi ngày",
    "hồ sơ gốc xác thực", "xác thực", "hồ sơ vụ án", "bộ công an", "trọng án", "sinh mạng", "nạn nhân",
}


# Canonical cross-script & Sino-Korean (한자음) <-> Mandarin (원음) equivalence groups.
# "person_*" and "org_*" are high-specificity unique case identifiers;
# "place_*" are geographic canonical tokens used in multi-entity matching.
CANONICAL_ENTITY_ALIASES: list[tuple[str, tuple[str, ...]]] = [
    # High-specificity suspect / organization / project identities
    ("person_gao_chengyong", ("고승용", "가오청융", "cao thừa dũng", "gao chengyong", "高承勇")),
    ("person_lao_rongzhi", ("라오룽즈", "노영지", "lao vinh chi", "lao rongzhi", "劳荣枝", "파즈잉", "법자영", "法子英")),
    ("person_zhou_kehua", ("주커화", "주극화", "chu khắc hoa", "zhou kehua", "폭두남", "周克华")),
    ("person_liu_yongbiao", ("유영표", "류융뱌오", "lưu vĩnh bưu", "liu yongbiao", "刘永彪", "汪维明")),
    ("person_ji_siguang", ("길광", "길사광", "지쓰광", "cát quang", "cát tứ quang", "ji siguang", "吉思光")),
    ("person_xiao_qiqiang", ("소기강", "샤오치창", "tiêu kỳ cường", "xiao qiqiang", "萧奇强", "肖奇强")),
    ("person_xiang_nanfang", ("행남방", "샹난팡", "hướng nam phương", "xiang nanfang", "向南方")),
    ("person_ma_jiajue", ("마가작", "마지아주에", "mã gia tước", "ma jiajue", "马加爵")),
    ("person_xie_renliang", ("시에런량", "셰런량", "사임량", "tạ nhân lương", "xie renliang", "谢仁良")),
    ("person_chen_xunmin", ("천쉰민", "진순민", "trần tuần mẫn", "chen xunmin", "陈恂敏", "陈恩年")),
    ("person_bai_baoshan", ("바이바오산", "백보산", "bạch bảo sơn", "bai baoshan", "白宝山")),
    ("person_wu_xieyu", ("우시에위", "우셰위", "오사우", "ngô tạ vũ", "wu xieyu", "吴谢宇")),
    ("person_zhang_liwei", ("장립위", "장리웨이", "trương lập vĩ", "zhang liwei", "张立伟")),
    ("person_xu_li", ("쉬리", "서리 사건", "보석상 사건과 서리", "từ lợi", "xu li", "徐利", "绿洲珠宝")),
    ("person_xu_chaofan", ("쉬차오판", "허초범", "쉬궈쥔", "허국준", "위전둥", "여진동", "hứa siêu phàm", "xu chaofan", "许超凡", "许国俊", "余振东")),
    ("person_ren_xiaofeng", ("런샤오펑", "임소봉", "마샹징", "마향경", "nhậm hiểu phong", "ren xiaofeng", "任晓峰", "马向景")),
    ("person_gao_shan_boc", ("가오산", "고산 지점장", "하얼빈 고산", "허쑹제", "하송가", "리둥저", "이동철", "고산 사건", "高山", "李东哲", "河松街")),
    ("person_zhang_shuhai", ("장수하이", "장서해", "trương thư hải", "zhang shuhai", "张书海")),
    ("person_shi_erqun", ("스얼췬", "석얼군", "thạch nhị quần", "shi erqun", "石二群")),
    ("person_ma_hanqing", ("마한칭", "마한경", "mã hán khánh", "ma hanqing", "马汉庆")),
    ("person_lei_guomin", ("레이궈민", "뢰국민", "이국민", "lôi quốc dân", "lei guomin", "雷国民")),
    ("person_xiang_shengyuan", ("샹성위안", "항생원", "hạng sinh nguyên", "xiang shengyuan", "项生源")),
    ("person_hou_jinliang", ("허우진량", "후금량", "hầu kim lượng", "hou jinliang", "侯金亮")),
    ("person_dong_wenyu", ("둥원위", "동문어", "đổng văn ngữ", "dong wenyu", "董文语")),
    ("person_yang_xinhai", ("양신하이", "양신해", "dương tân hải", "yang xinhai", "杨新海")),
    ("person_jin_ruchao", ("진루차오", "근여초", "cận như siêu", "jin ruchao", "靳如超")),
    ("person_sun_xiaoguo", ("쑨샤오궈", "손소과", "tôn tiểu quả", "sun xiaoguo", "孙小果")),
    ("person_yu_huaying", ("여화영", "위화잉", "양뉴화", "dư hoa anh", "dương nữu hoa", "余华英", "杨妞花")),
    ("person_xu_guoli", ("허궈리", "쉬궈리", "허국리", "hứa quốc lợi", "xu guoli", "许国利", "来惠利")),
    ("person_zhang_yongming", ("장융밍", "장영명", "남문촌", "thôn nam môn", "trương vĩnh minh", "张永明", "南门村")),
    ("person_qian_zhimin", ("첸즈민", "전민지", "람천격예", "블루스카이그리", "tiền chí mẫn", "qian zhimin", "钱志敏", "蓝天格锐")),
    ("person_qiao_jianjun", ("차오젠쥔", "교건군", "중추량", "중저량", "kiều kiến quân", "qiao jianjun", "乔建军", "中储粮")),
    ("person_yan_yongming", ("옌융밍", "염영명", "통화진마", "통화금마", "diêm vĩnh minh", "yan yongming", "闫永明", "通化金马")),
    ("person_dai_xuemin", ("다이쉐민", "대학민", "đới học dân", "dai xuemin", "戴学民")),
    ("person_wu_gang_jilin", ("지린 우강", "우강 방송", "ngô cương cát lâm", "吴刚")),
    ("person_chen_manxiong", ("천만슝", "진만웅", "천추위안", "진추원", "trần mãn hùng", "chen manxiong", "陈满雄", "陈秋园")),
    ("person_yang_xiuzhu", ("양슈주", "양수주", "dương tú châu", "yang xiuzhu", "杨秀珠")),
    ("person_lai_changxing", ("라이창싱", "뢰창성", "위안화 밀수", "원화 밀수", "lại xương tinh", "lai changxing", "赖昌星", "远华案")),
    ("person_li_huabo", ("리화보", "이화파", "포양현 재정국", "lý hoa ba", "li huabo", "李华波")),
    ("person_zhang_jun", ("장쥔 일당", "창더 9 1", "상덕 9 1", "장군 무장", "trương quân", "张君")),
    ("org_kingold_jewelry", ("진황주얼리", "금황주얼리", "진황 주얼리", "금황 주얼리", "자즈훙", "가지굉", "kim hoàng", "kingold", "金凰珠宝", "贾志宏")),
    ("org_ezubao", ("이주바오", "역조보", "ezubao", "e租宝", "딩닝", "丁宁")),
    ("org_aifujia", ("아이푸자", "애복가", "주즈핑", "주지평", "차오빈", "ái phúc gia", "aifujia", "爱福家", "朱志平", "曹斌")),
    ("org_shengdajinxi", ("성다진시", "성대금희", "판지뱌오", "판허쥔", "thịnh đại kim hỷ", "thịnh đại kim hi", "盛大金禧", "盘继彪")),
    ("org_plustoken", ("플러스토큰", "plustoken", "plus token", "딩잔칭", "바누아투")),
    ("org_shanxinhui", ("선신후이", "산신후이", "선심회", "장톈밍", "장천명", "thiện tâm hội", "善心汇", "张天明")),
    ("org_qianbao_zhang_xiaolei", ("첸바오왕", "전보망", "장샤오레이", "장소뢰", "tiền bảo võng", "trương tiểu lôi", "钱宝网", "张小雷")),
    ("org_tuandai_tang_jun", ("퇀다이왕", "투안다이왕", "단대망", "탕쥔", "당군", "đoàn đại võng", "đường quân", "团贷网", "唐军")),
    ("org_fanya_shan_jiuliang", ("판야", "범아", "판야 금속", "판야 유색금속", "산주량", "단주량", "단구량", "인듐", "phàn á", "đơn cửu lương", "泛亚有色", "单九良")),
    ("org_baoshang_bank", ("바오상은행", "포상은행", "바오상", "민톈그룹", "샤오젠화", "초건화", "包商银行", "肖建华")),
    ("org_henan_village_banks", ("허난 촌진은행", "하남 촌진은행", "촌진은행", "뤼이", "여혁", "신차이푸", "ngân hàng thôn trấn hà nam", "lữ dịch", "河南村镇银行", "吕奕")),
    ("org_nanjing_fake_bank", ("난징 가짜 은행", "남경 가짜 은행", "가짜 국유 은행", "류광밍", "유광명", "ngân hàng giả nam kinh", "lưu quang minh", "南京假银行", "刘光明")),
    ("person_wu_ying_bense", ("우잉", "오영", "본색그룹", "번써그룹", "ngô anh", "tập đoàn bổn sắc", "吴英", "本色集团")),
    ("person_sun_delin_shenyang38", ("순더린", "손덕림", "왕자리", "선양 3 8", "심양 3 8", "tôn đức lâm", "孙德林", "汪家礼")),
    ("person_jiang_yingku_zhaodong", ("장잉쿠", "장영고", "자오둥 장잉쿠", "tưởng anh khôi", "蒋英库")),
    ("person_wang_haijian_wuhan121", ("왕하이젠", "왕해검", "우한 12 1", "vương hải kiếm", "王海剑")),
    ("person_cheng_ruilong", ("청루이룽", "성서룡", "런추우", "trình thụy long", "cheng ruilong", "程瑞龙")),
    ("person_zhao_zhihong", ("자오즈훙", "조지홍", "후거지러투", "호격길륵도", "triệu chí hồng", "hô cách cát lặc đồ", "赵志红", "呼格吉勒图")),
    ("person_huang_yong_pingyu", ("황융", "황용", "핑위현", "평여현", "hoàng dũng", "huang yong", "黄勇")),
    ("person_dong_wanchun", ("둥완춘", "동만춘", "đổng vạn xuân", "dong wanchun", "董万春")),
    ("person_peng_miaoji", ("펑먀오지", "팽묘계", "bành diệu kế", "peng miaoji", "彭妙计")),
    ("person_wang_qiang_liaoning", ("왕창", "왕강", "vương cường", "wang qiang", "王强")),
    ("person_long_zhimin", ("룽즈민", "용지민", "상뤄", "long trị dân", "long zhimin", "龙治民")),
    ("person_zhu_xianjian", ("주셴젠", "주현건", "chu hiền kiện", "zhu xianjian", "朱贤健")),
    # Geographic & institutional Sino-Korean <-> Mandarin equivalents
    ("place_zhejiang", ("저장성", "저장", "절강성", "절강", "chiết giang", "zhejiang", "浙江")),
    ("place_shenzhen", ("선전", "심천", "thâm quyến", "thẩm quyến", "shenzhen", "深圳")),
    ("place_kaiping", ("카이핑", "개평", "khai bình", "kaiping", "开平")),
    ("place_handan", ("한단", "감단", "hàm đan", "handan", "邯郸")),
    ("place_harbin", ("하얼빈", "합이빈", "cáp nhĩ tân", "harbin", "哈尔滨")),
    ("place_ningbo", ("닝보", "영파", "ninh ba", "ningbo", "宁波")),
    ("place_shaoxing", ("샤오싱", "소흥", "thiệu hưng", "shaoxing", "绍兴")),
    ("place_zhengzhou", ("정저우", "정주", "trịnh châu", "zhengzhou", "郑州")),
    ("place_zhumadian", ("주마뎬", "주마점", "trú mã điếm", "zhumadian", "驻马店")),
    ("place_fuyang", ("푸양", "부양", "phụ dương", "fuyang", "阜阳")),
    ("place_jiuhuashan", ("구화산", "주화산", "cửu hoa sơn", "jiuhuashan", "九华山")),
    ("place_longxing_temple", ("용흥사", "롱싱사", "chùa long hưng", "longxing", "龙兴寺")),
    ("place_xiaoshan", ("샤오산", "소산", "tiêu sơn", "xiaoshan", "萧山")),
    ("place_wenxi", ("원시현", "문희현", "văn hỷ", "wenxi", "闻喜")),
    ("place_wuhan", ("우한", "무한", "vũ hán", "wuhan", "武汉")),
    ("place_wenzhou", ("원저우", "온주", "ôn châu", "wenzhou", "温州")),
    ("place_kaili", ("카이리", "개리", "khải lý", "kaili", "凯里")),
    ("place_baiyin", ("바이인", "백은시", "bạch ngân", "baiyin", "白银")),
    ("place_panyu", ("판위", "번우", "phiên ngung", "panyu", "番禺")),
    ("place_wanxiang_park", ("완샹공원", "만향공원", "vạn hướng", "万向公园")),
]


# Known high-specificity case anchor clusters
CASE_CLUSTERS: list[dict[str, Any]] = [
    {
        "key": "case_baiyin_serial_killer",
        "name": "Đại án Bạch Ngân Cao Thừa Dũng (Baiyin 28-year School Store Case)",
        "markers": [
            "bạch ngân", "baiyin", "바이인", "바이인시", "백은시", "白银",
            "cao thừa dũng", "gao chengyong", "고승용", "가오청융", "高承勇",
        ],
        "scenario_a": ["28년간", "28년", "28 năm", "28-year"],
        "scenario_b": [
            "학교 매점", "매점", "tiệm tạp hóa", "tạp hóa trường học", "grocery store", "school store",
            "y-염색체", "y-str", "nhiễm sắc thể y",
        ],
    },
    {
        "key": "case_lao_rongzhi",
        "name": "Đại án Lao Vinh Chi / Lao Rongzhi (20-year fugitive disguise)",
        "markers": [
            "lao rongzhi", "lao vinh chi", "라오룽즈", "노영지", "劳荣枝",
            "fa ziying", "파즈잉", "법자영", "法子英", "sherry", "hong moujiao", "홍모자오",
        ],
        "scenario_a": ["20년간", "20년", "20 năm", "20-year"],
        "scenario_b": [
            "신분을 세탁", "tẩy trắng thân phận", "thay tên đổi họ", "vỏ bọc",
            "백화점", "tiệm đồng hồ", "시계 매장", "watch counter", "안면인식",
        ],
    },
    {
        "key": "case_south_to_north_water_diversion",
        "name": "Đại công trình Nam Thủy Bắc Điều 1,432km & Đất trương nở / Đập Đan Giang Khẩu",
        "markers": [
            "nam thủy bắc điều", "south-to-north", "남수북조",
            "đan giang khẩu", "danjiangkou", "단장커우",
        ],
        "scenario_a": ["1432km", "1432 km", "1432킬로미터"],
        "scenario_b": [
            "đất trương nở", "팽창토", "expansive soil", "지반 침하",
            "sụt lún", "5000억 위안", "500 tỷ",
        ],
    },
    {
        "key": "case_zhou_kehua",
        "name": "Đại án Chu Khắc Hoa (8 năm vượt 10 tỉnh vây ráp hang núi)",
        "markers": ["chu khắc hoa", "zhou kehua", "주커화", "주극화", "폭두남", "周克华"],
        "scenario_a": ["8년간", "8년", "8 năm"],
        "scenario_b": ["동굴", "hang núi", "10개 성", "8개 성", "10 tỉnh", "걸음걸이", "dáng đi", "충칭", "가화산"],
    },
    {
        "key": "case_liu_yongbiao",
        "name": "Kỳ án Lưu Vĩnh Bưu / Nhà trọ Hồ Châu (22 năm ẩn mình thành nhà văn)",
        "markers": ["lưu vĩnh bưu", "liu yongbiao", "유영표", "류융뱌오", "호주 여관", "hồ châu", "刘永彪", "汪维明"],
        "scenario_a": ["22년간", "22년", "22 năm"],
        "scenario_b": ["작가", "nhà văn", "소설", "tiểu thuyết", "best seller", "베스트셀러", "여관"],
    },
    {
        "key": "case_ji_siguang",
        "name": "Kỳ án Cát Quang / Ji Siguang (13 năm trốn truy nã thành diễn viên phim truyền hình)",
        "markers": ["cát quang", "cát tứ quang", "ji siguang", "길광", "길사광", "지쓰광", "길광 도주", "吉思光"],
        "scenario_a": ["13년간", "13년", "13 năm"],
        "scenario_b": ["드라마 배우", "인기 드라마", "잠복", "diễn viên", "phim truyền hình", "엑스트라"],
    },
    {
        "key": "case_xiao_qiqiang",
        "name": "Kỳ án Tiêu Kỳ Cường / Xiao Qiqiang (17 năm giả câm điếc ăn xin trốn truy nã)",
        "markers": ["tiêu kỳ cường", "xiao qiqiang", "소기강", "샤오치창", "소기강 신분세탁", "萧奇强", "肖奇强"],
        "scenario_a": ["17년간", "17년", "17 năm"],
        "scenario_b": ["벙어리", "거지", "말을 잃어버린", "giả câm", "ăn xin", "mất tiếng"],
    },
    {
        "key": "case_xiang_nanfang",
        "name": "Vụ án Hướng Nam Phương / Xiang Nanfang (12 năm tẩy trắng thân phận thành triệu phú Vương Bân)",
        "markers": ["hướng nam phương", "xiang nanfang", "행남방", "샹난팡", "행남방 도주", "왕 빈", "왕빈", "向南方"],
        "scenario_a": ["12년간", "12년", "12 năm"],
        "scenario_b": ["수백만 위안 자산가", "자산가로 변신", "triệu phú", "자선가", "72시간"],
    },
    {
        "key": "case_ma_jiajue",
        "name": "Kỳ án Mã Gia Tước / Ma Jiajue (Ký túc xá ĐH Vân Nam 2004)",
        "markers": ["mã gia tước", "ma jiajue", "마가작", "마지아주에", "운남대 기숙사", "윈난대 기숙사", "马加爵"],
        "scenario_a": ["2004년", "2004", "4명", "bốn bạn", "53일간"],
        "scenario_b": ["기숙사", "벽장", "트럼프", "ký túc xá", "đánh bài", "명문대 우등생"],
    },
    {
        "key": "case_three_gorges_silt",
        "name": "Đập Tam Hiệp 1,9 tỷ tấn bùn cát & Xói ngầm hạ lưu",
        "markers": ["tam hiệp", "three gorges", "삼협댐", "싼샤댐"],
        "scenario_a": ["19억 톤", "1.9 tỷ tấn", "1900000000"],
        "scenario_b": ["청수세굴", "퇴적물", "xói ngầm", "bùn cát", "bồi lắng"],
    },
    {
        "key": "case_baihetan_dam",
        "name": "Siêu đập Bạch Hạc Than / Baihetan 289m không vết nứt",
        "markers": ["bạch hạc than", "baihetan", "바이허탄", "백학탄"],
        "scenario_a": ["289m", "289미터", "2200억 위안"],
        "scenario_b": ["균열 0", "저열 시멘트", "아치댐", "không vết nứt"],
    },
    {
        "key": "case_hangzhou_bay_bridge",
        "name": "Cầu vượt biển Vịnh Hàng Châu 36km",
        "markers": ["vịnh hàng châu", "hangzhou bay", "항저우만"],
        "scenario_a": ["36km", "36킬로미터"],
        "scenario_b": ["해상대교", "메탄가스", "조수간만"],
    },
    {
        "key": "case_sichuan_tibet_railway",
        "name": "Đường sắt Tứ Xuyên - Tây Tạng 3,200 tỷ tệ",
        "markers": ["tứ xuyên tây tạng", "sichuan tibet", "쓰촨 티베트", "천장철도"],
        "scenario_a": ["3조 2천억", "3000m"],
        "scenario_b": ["고원 철도", "단층대", "터널"],
    },
    {
        "key": "case_qian_zhimin_60k_btc",
        "name": "Đại án Tiền Chí Mẫn / Lam Thiên Cách Nhuệ (61.000 Bitcoin / 8.000 tỷ Won trong USB)",
        "markers": [
            "tiền chí mẫn", "qian zhimin", "첸즈민", "람천격예", "블루스카이그리",
            "lam thiên cách nhuệ", "6만 비트코인", "61000 btc", "钱志敏", "蓝天格锐",
        ],
        "scenario_a": ["8조 원", "12만 명", "6만 개"],
        "scenario_b": ["usb", "런던", "영국 경찰", "비트코인 세탁"],
    },
    {
        "key": "case_plustoken_30t",
        "name": "Đại án PlusToken 30.000 tỷ Won (Sorry, we have run / Vanuatu)",
        "markers": ["plustoken", "plus token", "플러스토큰", "딩잔칭", "천보", "바누아투", "vanuatu", "陈波", "丁赞清"],
        "scenario_a": ["30조 원", "200만 명", "194775"],
        "scenario_b": ["도망쳤다", "we have run", "유령 지갑", "28000"],
    },
    {
        "key": "case_xie_renliang_91m_bonds",
        "name": "Đại án Tạ Nhân Lương / Xie Renliang (91,5 triệu tệ công trái Thâm Quyến/Ninh Ba & 19 năm giả mất trí nhớ)",
        "markers": [
            "tạ nhân lương", "xie renliang", "시에런량", "셰런량", "사임량", "谢仁良",
            "심천 증권사 증발", "선전 증권사 증발", "9150만 위안", "915 triệu", "91 5 triệu",
        ],
        "scenario_a": ["19년", "19년간", "19 năm"],
        "scenario_b": ["이름 없는 환자", "기억상실", "mất trí nhớ", "국채", "công trái", "푸둥 공항", "증권"],
    },
    {
        "key": "case_chen_xunmin_15m_armored",
        "name": "Đại án Trần Tuần Mẫn / Chen Xunmin (Cướp xe chở tiền 15 triệu tệ Phiên Ngung 1995 & 21 năm bán gạch men)",
        "markers": [
            "trần tuần mẫn", "chen xunmin", "천쉰민", "진순민", "陈恂敏", "陈恩年",
            "1500만 위안 수송차", "번우 수송차", "판위 수송차", "番禺大劫案",
        ],
        "scenario_a": ["21년간", "21년", "21 năm"],
        "scenario_b": ["타일", "수송차", "xe chở tiền", "시골 가게 사장", "gạch men"],
    },
    {
        "key": "case_bai_baoshan",
        "name": "Đại án Bạch Bảo Sơn / Bai Baoshan (Truy nã số 1 năm 1997 vượt 3.000km Bắc Kinh - Tân Cương)",
        "markers": ["bạch bảo sơn", "bai baoshan", "바이바오산", "백보산", "白宝山"],
        "scenario_a": ["1997년", "3000km", "1만 페이지"],
        "scenario_b": ["광역 추적", "어머니", "단 한마디", "신장", "tân cương"],
    },
    {
        "key": "case_wu_xieyu",
        "name": "Đại án Ngô Tạ Vũ / Wu Xieyu (Thiên tài Bắc Đại & 1.380 ngày đào tẩu)",
        "markers": ["ngô tạ vũ", "wu xieyu", "우시에위", "우셰위", "오사우", "吴谢宇"],
        "scenario_a": ["1380일", "1 380일"],
        "scenario_b": ["북경대", "베이징대", "가짜 편지", "bắc đại", "bức thư giả"],
    },
    {
        "key": "case_nanjing_med_324",
        "name": "Kỳ án Đại học Y Nam Kinh 3·24 / Ma Lin (28 năm phá án nhờ ADN họ hàng)",
        "markers": ["난징 의대", "남경 의대", "đại học y nam kinh", "南京医学院", "麻林"],
        "scenario_a": ["3 24", "28년간", "28년", "28 năm"],
        "scenario_b": ["여대생 미제", "모범 시민", "1만 5000명", "1만 5 000명", "1 5km"],
    },
    {
        "key": "case_kaili_le_xianjiang",
        "name": "Đại án Khải Lý Quý Châu (16 năm sát vách đồn cảnh sát - gia đình Giám đốc Ngân hàng Khải Lý)",
        "markers": ["카이리", "개리", "khải lý", "凯里", "乐贵建", "黄德坤", "潘凯平"],
        "scenario_a": ["16년", "16년간", "16 năm"],
        "scenario_b": ["은행장 가족", "옆집 이웃", "현직 공직자", "두 사건"],
    },
    {
        "key": "case_yu_huaying_yang_niuhua",
        "name": "Đại án Dư Hoa Anh & Dương Nữu Hoa (26 năm vẽ bản đồ ký ức tự bắt kẻ buôn người)",
        "markers": ["여화영", "위화잉", "양뉴화", "dư hoa anh", "dương nữu hoa", "余华英", "杨妞花"],
        "scenario_a": ["26년", "26년간", "26 năm", "5살 때"],
        "scenario_b": ["기억의 지도", "유괴된 소녀", "bản đồ ký ức"],
    },
    {
        "key": "case_xu_guoli_hangzhou",
        "name": "Đại án Hứa Quốc Lợi / Hàng Châu (6.000 mắt camera & 20g manh mối hầm tự hoại)",
        "markers": ["hứa quốc lợi", "xu guoli", "허궈리", "쉬궈리", "허국리", "许国利", "来惠利", "항저우 아파트 실종", "항저우 실종"],
        "scenario_a": ["6000개", "6 000개", "6천 개", "6000"],
        "scenario_b": ["정화조", "hầm tự hoại", "20그램", "20 gram", "20g"],
    },
    {
        "key": "case_sun_xiaoguo",
        "name": "Đại án Tôn Tiểu Quả / Sun Xiaoguo (Tử tù 'hồi sinh' sau 21 năm tại Côn Minh)",
        "markers": ["tôn tiểu quả", "sun xiaoguo", "쑨샤오궈", "손소과", "孙小果"],
        "scenario_a": ["21년 만에", "21 năm"],
        "scenario_b": ["되살아난 사형수", "사형 집행", "tử tù"],
    },
    {
        "key": "case_nanmen_village",
        "name": "Kỳ án Thôn Nam Môn Vân Nam / Trương Vĩnh Minh (17 thanh thiếu niên mất tích bán kính 1km)",
        "markers": ["남문촌", "thôn nam môn", "kỳ án nam môn", "南门村", "张永明", "장융밍", "장영명"],
        "scenario_a": ["17명", "17 thiếu niên", "17 thanh niên"],
        "scenario_b": ["반경 1km", "침묵의 외톨이"],
    },
    {
        "key": "case_zhang_liwei_monk_16y",
        "name": "Kỳ án Trương Lập Vĩ / Zhang Liwei (16 năm ẩn mình làm Trụ trì Chùa Long Hưng)",
        "markers": [
            "장립위", "장리웨이", "trương lập vĩ", "zhang liwei", "张立伟",
            "용흥사", "롱싱사", "chùa long hưng", "龙兴寺",
        ],
        "scenario_a": ["16년간", "16년", "16 năm"],
        "scenario_b": ["주지 스님", "주지스님", "사찰", "고찰", "trụ trì", "sư trụ trì"],
    },
    {
        "key": "case_xu_li_zhejiang_no1",
        "name": "Đệ nhất Kỳ án Chiết Giang / Từ Lợi (22 năm vụ cướp tiệm vàng Lục Châu Ninh Ba & Thiệu Hưng)",
        "markers": [
            "쉬리", "보석상 사건과 서리", "서리 사건", "từ lợi", "xu li", "徐利",
            "뤼저우 보석", "녹주 보석", "绿洲珠宝", "절강 제1", "저장성 제1", "저장 제1", "浙江第一悬案",
        ],
        "scenario_a": ["22년간", "22년", "22 năm"],
        "scenario_b": ["보석상", "닝보", "영파", "샤오싱", "소흥", "tiệm vàng"],
    },
    {
        "key": "case_kaiping_boc_4b",
        "name": "Đại án Ngân hàng Trung Quốc Khai Bình 485 triệu USD / 4 tỷ tệ (Hứa Siêu Phàm - Dư Chấn Đông - Hứa Quốc Tuấn)",
        "markers": [
            "카이핑", "개평", "khai bình", "kaiping", "开平",
            "쉬차오판", "허초범", "쉬궈쥔", "허국준", "위전둥", "여진동", "许超凡", "许国俊", "余振东",
        ],
        "scenario_a": ["40억 위안", "39억 위안", "4억 8500만 달러", "4 85억 달러", "485 triệu usd", "4 tỷ nhân dân tệ"],
        "scenario_b": ["은행 금고", "중국은행", "지점장", "라스베이거스", "위장결혼"],
    },
    {
        "key": "case_handan_abc_51m_lottery",
        "name": "Đại án Ngân hàng Nông nghiệp Hàm Đan 51 triệu tệ mua vé số (Nhậm Hiểu Phong & Mã Hướng Cảnh)",
        "markers": [
            "한단 농업은행", "감단 농업은행", "런샤오펑", "임소봉", "마샹징", "마향경",
            "任晓峰", "马向景", "邯郸农行",
        ],
        "scenario_a": ["5100만 위안", "4300만 위안", "51 triệu nhân dân tệ", "51 triệu tệ"],
        "scenario_b": ["복권", "금고 관리자", "vé số", "농업은행"],
    },
    {
        "key": "case_gao_shan_harbin_boc_1b",
        "name": "Đại án Cao Sơn / Chi nhánh Hà Tùng Nhai Cáp Nhĩ Tân 1 tỷ tệ (Cao Sơn & Lý Đông Triết)",
        "markers": [
            "가오산", "하얼빈 고산", "고산 사건", "허쑹제", "하송가", "리둥저", "이동철",
            "高山", "李东哲", "河松街",
        ],
        "scenario_a": ["10억 위안", "1 tỷ nhân dân tệ", "1 tỷ tệ"],
        "scenario_b": ["하얼빈 중국은행", "유령 계좌", "캐나다", "가짜 도장", "법인 계좌"],
    },
    {
        "key": "case_zhang_shuhai_zhengzhou_125",
        "name": "Đại án Trương Thư Hải / Nổ kính chống đạn Ngân hàng Hợp tác Trịnh Châu 12·5 (2000)",
        "markers": ["장수하이", "장서해", "trương thư hải", "zhang shuhai", "张书海", "정저우 12 5"],
        "scenario_a": ["5분", "208만 위안"],
        "scenario_b": ["방탄유리", "폭약", "정저우", "정주", "kính chống đạn"],
    },
    {
        "key": "case_shi_erqun_zhumadian_1999",
        "name": "Đại án Thạch Nhị Quần / Trú Mã Điếm 1999 (16 năm biến thành đại gia bất động sản)",
        "markers": ["스얼췬", "석얼군", "thạch nhị quần", "shi erqun", "石二群", "주마뎬", "주마점", "驻马店"],
        "scenario_a": ["16년간", "16년", "16 năm"],
        "scenario_b": ["부동산 재벌", "방탄유리", "자선가", "bất động sản"],
    },
    {
        "key": "case_kingold_83t_fake_gold",
        "name": "Đại án Vàng giả mạ đồng 83 tấn Kim Hoàng / Kingold Jewelry Vũ Hán (Giả Chí Hoành)",
        "markers": [
            "진황주얼리", "금황주얼리", "진황 주얼리", "금황 주얼리", "자즈훙", "가지굉",
            "kim hoàng", "kingold", "金凰珠宝", "贾志宏",
        ],
        "scenario_a": ["83톤", "83 tấn", "160억 위안", "200억 위안"],
        "scenario_b": ["구리", "가짜 금괴", "금괴", "담보", "mạ đồng", "thỏi vàng"],
    },
    {
        "key": "case_ezubao_ding_ning",
        "name": "Đại án Ponzi eZubao / Đinh Ninh (9.000 tỷ Won / 900.000 nạn nhân & 1.200 sổ cái chôn sâu 6m)",
        "markers": ["이주바오", "역조보", "ezubao", "e租宝", "딩닝", "丁宁"],
        "scenario_a": ["9조 원", "500억 위안", "762억 위안", "90만 명", "1200권"],
        "scenario_b": ["땅속", "6미터", "6m", "굴착기", "비밀 장부", "p2p"],
    },
    {
        "key": "case_aifujia_zhu_zhiping",
        "name": "Đại án Ái Phúc Gia / Chu Chí Bình - Tào Bân (Dưỡng lão 2.000 tỷ Won / 100.000 người nghỉ hưu)",
        "markers": ["아이푸자", "애복가", "주즈핑", "주지평", "차오빈", "ái phúc gia", "aifujia", "爱福家", "朱志平", "曹斌"],
        "scenario_a": ["수백억", "노후 자금", "퇴직금", "2조", "106억 위안", "10만 은퇴자"],
        "scenario_b": ["조개껍데기", "생태 양로", "양로원", "무료 건강검진", "효도 관광", "양로 사기", "vỏ sò", "dưỡng lão"],
    },
    {
        "key": "case_nanjing_fake_bank",
        "name": "Đại án Ngân hàng Quốc doanh Giả Nam Kinh (200 người gửi 400 triệu tệ / 70 tỷ Won)",
        "markers": ["난징 가짜 은행", "남경 가짜 은행", "류광밍", "유광명", "ngân hàng giả nam kinh", "南京假银行", "刘光明"],
        "scenario_a": ["4억 위안", "700억", "200명", "4200만 위안"],
        "scenario_b": ["가짜 국유 은행", "가짜 은행", "led 전광판", "청원경찰", "ngân hàng giả"],
    },
    {
        "key": "case_shengdajinxi",
        "name": "Đại án Thịnh Đại Kim Hỷ / Bàn Kế Bưu (19 tỷ tệ Ponzi lãi suất 14% suốt 11 năm)",
        "markers": ["성다진시", "성대금희", "판지뱌오", "thịnh đại kim hỷ", "盛大金禧", "盘继彪"],
        "scenario_a": ["190억 위안", "10만 명", "14%"],
        "scenario_b": ["퇴직금", "원금 보장", "창사", "장사"],
    },
    {
        "key": "case_qiao_jianjun_sinograin",
        "name": "Đại án Kiều Kiến Quân / Kho dự trữ lương thực Trung Trữ Lương Chu Khẩu (Hạt thóc ma 700 triệu tệ)",
        "markers": ["차오젠쥔", "교건군", "중추량", "중저량", "kiều kiến quân", "qiao jianjun", "乔建军", "中储粮"],
        "scenario_a": ["7억 위안", "2억 위안", "수만 톤"],
        "scenario_b": ["유령 곡물", "국가 비축미", "창고", "스웨덴", "미국"],
    },
    {
        "key": "case_yan_yongming_tonghua_jinma",
        "name": "Đại án Diêm Vĩnh Minh / Thông Hóa Kim Mã (Đốt hàng trăm triệu tại sòng bài New Zealand suốt 15 năm)",
        "markers": ["옌융밍", "염영명", "통화진마", "통화금마", "diêm vĩnh minh", "yan yongming", "闫永明", "通化金马"],
        "scenario_a": ["15년간", "15년", "82분", "3억 위안", "12억 위안"],
        "scenario_b": ["뉴질랜드", "카지노", "제약회사", "백인 홍색 수배 5호"],
    },
    {
        "key": "case_dai_xuemin_china_trust",
        "name": "Đại án Đới Học Dân / Tín thác Kinh tế Trung Quốc (Người đầu tiên sa lưới Chiến dịch Săn Cáo 19 năm)",
        "markers": ["다이쉐민", "대학민", "đới học dân", "dai xuemin", "戴学民", "중국경제개발신탁"],
        "scenario_a": ["1100만 위안", "19년"],
        "scenario_b": ["여권 위조", "얼굴 스캔", "상하이", "여우사냥"],
    },
    {
        "key": "case_chen_manxiong_zhongshan",
        "name": "Đại án Trần Mãn Hùng & Trần Thu Viên / Ngân hàng Trung Sơn (420 triệu tệ sòng bài Macau & phẫu thuật toàn diện ở Thái Lan)",
        "markers": ["천만슝", "진만웅", "천추위안", "진추원", "trần mãn hùng", "chen manxiong", "陈满雄", "陈秋园"],
        "scenario_a": ["4억 2000만 위안", "4 2억 위안", "420 triệu"],
        "scenario_b": ["태국", "전신 성형", "얼굴 성형", "마카오 카지노", "중산 실업은행"],
    },
    {
        "key": "case_ma_hanqing_manhunt",
        "name": "Chuyên án Mã Hán Khánh / Ma Hanqing (8 năm trốn truy nã cấp A từ Vũ Hán tới Tam Á & Tân Cương)",
        "markers": ["마한칭", "마한경", "mã hán khánh", "ma hanqing", "马汉庆"],
        "scenario_a": ["8년간", "8년", "8 năm"],
        "scenario_b": ["우한", "무한", "싼야", "삼아", "신장", "택시기사"],
    },
    {
        "key": "case_lei_guomin_vault_torch",
        "name": "Chuyên án Lôi Quốc Dân / Lei Guomin (Độc hành dùng đèn khò oxy-gas cắt két sắt ngân hàng xuyên 7 tỉnh)",
        "markers": ["레이궈민", "뢰국민", "이국민", "lôi quốc dân", "lei guomin", "雷国民"],
        "scenario_a": ["9년간", "9년", "7개 성"],
        "scenario_b": ["산소절단기", "산소 절단기", "금고 절단", "단독 습격", "đèn khò"],
    },
    {
        "key": "case_xiang_shengyuan_xiaoshan_28y",
        "name": "Kỳ án Hạng Sinh Nguyên / Tiêu Sơn Hàng Châu (28 năm giải mã hai vụ án tài xế taxi năm 1995 nhờ ADN gia phả)",
        "markers": ["샹성위안", "항생원", "hạng sinh nguyên", "xiang shengyuan", "项生源", "샤오산 미제", "소산 미제"],
        "scenario_a": ["샤오산", "소산", "항생원", "샹성위안", "tiêu sơn", "hạng sinh nguyên"],
        "scenario_b": ["28년", "28년간", "1995년", "택시", "담배꽁초"],
    },
    {
        "key": "case_hou_jinliang_wenxi_tombs",
        "name": "Đại án Hầu Kim Lượng / Tập đoàn trộm mộ cổ Văn Hỷ Sơn Tây & cổ vật quốc bảo cấp 1",
        "markers": ["허우진량", "후금량", "hầu kim lượng", "hou jinliang", "侯金亮", "원시현 고분", "문희현 고분"],
        "scenario_a": ["1급 문물", "수백 점", "고분군"],
        "scenario_b": ["도굴", "청동기", "원시현", "문희현", "보호우산"],
    },
    {
        "key": "case_dong_wenyu_6prov",
        "name": "Chuyên án Đổng Văn Ngữ / Dong Wenyu (Truy nã cấp A xuyên 6 tỉnh ẩn náu rừng sâu)",
        "markers": ["둥원위", "동문어", "đổng văn ngữ", "dong wenyu", "董文语"],
        "scenario_a": ["6개 성", "6 tỉnh"],
        "scenario_b": ["산속", "야간", "전단", "지문"],
    },
    {
        "key": "case_hangzhou_wanxiang_park_20y",
        "name": "Kỳ án Công viên Vạn Hướng Hàng Châu (3 thế hệ cảnh sát tiếp sức 20 năm truy tọa độ ADN 1.200km)",
        "markers": ["완샹공원", "만향공원", "vạn hướng", "万向公园"],
        "scenario_a": ["20년", "20년간", "1200km"],
        "scenario_b": ["3대 형사", "도심 공원", "항저우"],
    },
    {
        "key": "case_jin_ruchao_168h",
        "name": "Chuyên án 168 giờ đại truy kích Cận Như Siêu / Jin Ruchao (2.400km Hà Bắc - Bắc Hải Quảng Tây)",
        "markers": ["진루차오", "근여초", "cận như siêu", "jin ruchao", "靳如超", "스자좡 3 16"],
        "scenario_a": ["168시간", "168 giờ", "2400km"],
        "scenario_b": ["청력을 잃은", "베이하이", "북해", "수배 전단"],
    },
]


_HANZI_BLOCK_RE = re.compile(r"[\u4e00-\u9fff]{2,8}")
_HANZI_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")
_DISTINCTIVE_METRIC_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(톤|tấn|만\s*위안|억\s*위안|억\s*달러|조\s*원|km|킬로미터|m|미터|일|시간|giờ|비트코인|btc)\b"
)
_METRIC_MATCH_RE = re.compile(
    r"(\d+[\.,]?\d*\s*(?:년간|년|năm|km|킬로미터|억 위안|만 위안|억 달러|조 원|tỷ|triệu|톤|tấn|m³|phút|giây|미터|시간|일))",
    re.IGNORECASE,
)
_HANGUL_ENTITY_RE = re.compile(r"([가-힣]{3,}(?:시|성|사건|공정|수배범)?)")
_NUMERIC_UNIT_FULL_RE = re.compile(r"\d+(?:\.\d+)?(?:년|년간|억|만|조|톤|km|m|일|시간)?")
_ANCHOR_NUM_FULL_RE = re.compile(
    r"\d+[\.,]?\d*\s*(?:년간|년|năm|km|킬로미터|억|조|만|미터|일|개월|시간|%|자루의|그램의)?"
)

_PREPARED_CANONICAL_ALIASES: list[tuple[str, bool, tuple[str, ...]]] = [
    (
        canon_id,
        canon_id.startswith("place_"),
        tuple(
            v_norm
            for v in variants
            for v_norm in ((_normalize_text(v) if not _HANZI_CHAR_RE.search(v) else v.lower()),)
            if v_norm
        ),
    )
    for canon_id, variants in CANONICAL_ENTITY_ALIASES
]

_PREPARED_CASE_CLUSTERS: list[dict[str, Any]] = [
    {
        "cluster": cluster,
        "name": cluster["name"],
        "markers": tuple(cluster["markers"]),
        "markers_pairs": tuple((m, _normalize_text(m), m.lower()) for m in cluster["markers"]),
        "scenario_a": tuple(cluster["scenario_a"]),
        "scen_a_pairs": tuple((sa, _normalize_text(sa)) for sa in cluster["scenario_a"]),
        "scenario_b": tuple(cluster["scenario_b"]),
        "scen_b_pairs": tuple((sb, _normalize_text(sb)) for sb in cluster["scenario_b"]),
    }
    for cluster in CASE_CLUSTERS
]


_HANZI_EDGE_GENERIC_RE = re.compile(
    r"^(?:年|月|日|个|十|百|千|万|亿|余|名|起|件|省|市|县|区|亿美元|亿元|万元|美元|元|公斤|吨|小时|天|跨省|跨国|跨|两起|系列|特大|惊天|真实|命案|重案|积案|悬案|逃犯|主犯|嫌犯|疑犯|犯罪|团伙|警方|公安部|公安|刑警|经侦|侦破|破案|锁定|真凶|抓捕|追捕|围捕|落网|归案|潜逃|挪用|贪污|诈骗|非法集资|崩盘|公款|纪实)+"
    r"|(?:侦破纪实|破案纪实|侦破案|侦破|破案|潜逃案|潜逃|追捕案|大追捕|追捕|围捕案|大围捕|围捕|被盗案|被盗|抢劫案|劫案|越狱案|越狱|贪污案|挪用公款案|挪用案|挪用|非法集资崩盘案|非法集资案|非法集资|崩盘案|崩盘|集资诈骗案|诈骗案|走私案|专案|大案|案件|纪实|锁定真凶案|锁定真凶|真凶案|真凶|落网案|落网|归案|公款案|公款|逃犯|主犯|嫌犯|案|事件|省|市|县|区|年|月|日|亿元|万元|亿美元|元)+$"
)


@lru_cache(maxsize=8192)
def _extract_hanzi_anchors_cached(text: str) -> tuple[str, ...]:
    if not text:
        return ()
    blocks = _HANZI_BLOCK_RE.findall(text)
    out: list[str] = []
    for raw_b in blocks:
        if raw_b in GENERIC_HANZI_STOPWORDS:
            continue
        cleaned_b = raw_b
        for _ in range(3):
            next_b = _HANZI_EDGE_GENERIC_RE.sub("", cleaned_b).strip()
            if next_b == cleaned_b:
                break
            cleaned_b = next_b
        if (
            len(cleaned_b) >= 2
            and cleaned_b not in GENERIC_HANZI_STOPWORDS
            and not _HANZI_EDGE_GENERIC_RE.fullmatch(cleaned_b)
            and cleaned_b not in out
        ):
            out.append(cleaned_b)
    return tuple(out)


def _extract_hanzi_anchors(text: str) -> list[str]:
    return list(_extract_hanzi_anchors_cached(text or ""))


@lru_cache(maxsize=8192)
def _extract_canonical_alias_ids_cached(norm_text: str, raw_text_low: str = "") -> tuple[frozenset[str], frozenset[str]]:
    unique_ids: set[str] = set()
    place_ids: set[str] = set()
    haystack = f"{norm_text} {raw_text_low}"
    for canon_id, is_place, v_norms in _PREPARED_CANONICAL_ALIASES:
        for v_norm in v_norms:
            if v_norm in haystack:
                if is_place:
                    place_ids.add(canon_id)
                else:
                    unique_ids.add(canon_id)
                break
    return frozenset(unique_ids), frozenset(place_ids)


def _extract_canonical_alias_ids(norm_text: str, raw_text: str = "") -> tuple[set[str], set[str]]:
    """
    Return `(unique_case_ids, place_ids)` matched across Sino-Korean, Mandarin,
    Vietnamese, English, and Chinese Hanzi variants.
    """
    u, p = _extract_canonical_alias_ids_cached(norm_text, (raw_text or "").lower())
    return set(u), set(p)


@lru_cache(maxsize=8192)
def _extract_distinctive_metrics_cached(norm_text: str) -> frozenset[str]:
    out: set[str] = set()
    for m in _DISTINCTIVE_METRIC_RE.finditer(norm_text):
        num_str = m.group(1)
        unit = m.group(2).replace(" ", "")
        # Canonicalize unit across KR/VI/EN where unambiguous
        unit_canon = {
            "tấn": "톤",
            "킬로미터": "km",
            "미터": "m",
            "giờ": "시간",
            "비트코인": "btc",
        }.get(unit, unit)
        try:
            val = float(num_str)
        except ValueError:
            continue
        if num_str.startswith("0") or val <= 0:
            continue
        # Filter out round generic numbers like 10억, 100억, 1km, 24시간, 72시간 unless multi-digit specific
        if unit_canon in {"톤", "일", "km", "m", "시간", "btc"} and val not in {1, 2, 3, 5, 7, 8, 10, 12, 14, 15, 20, 24, 30, 48, 72, 100, 1000}:
            out.add(f"{num_str}:{unit_canon}")
        elif unit_canon in {"만위안", "억위안", "억달러", "조원"} and val not in {1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 30, 50, 100, 1000}:
            out.add(f"{num_str}:{unit_canon}")
    return frozenset(out)


def _extract_distinctive_metrics(norm_text: str) -> set[str]:
    """
    Extract rare / non-generic numbers + unit fingerprints (excluding common small integers like 10년/20년 alone).
    Examples: '83톤', '9150만', '5100만', '1380일', '1432km', '289m', '168시간', '61000', '194775'.
    """
    return set(_extract_distinctive_metrics_cached(norm_text or ""))


@lru_cache(maxsize=8192)
def _extract_case_anchors_and_entities_cached(
    title: str, topic: str = "", notes: str = ""
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    combined = f"{title} {topic} {notes}".strip()
    combined_low = combined.lower()
    norm = _normalize_text(combined)

    entities: list[str] = []
    keywords: list[str] = []

    # 1. Match known case clusters
    for pc in _PREPARED_CASE_CLUSTERS:
        has_marker = any((m_norm and m_norm in norm) or m_low in combined_low for _, m_norm, m_low in pc["markers_pairs"])
        has_scen_a = any(sa_norm in norm for _, sa_norm in pc["scen_a_pairs"])
        has_scen_b = any(sb_norm in norm for _, sb_norm in pc["scen_b_pairs"])
        if has_marker or (has_scen_a and has_scen_b):
            for m in pc["markers"][:3]:
                if m not in entities:
                    entities.append(m)
            for s in pc["scenario_a"][:2] + pc["scenario_b"][:3]:
                if s not in keywords:
                    keywords.append(s)

    # 1b. Canonical Sino-Korean / Mandarin / Hanzi alias IDs
    canon_unique, canon_places = _extract_canonical_alias_ids_cached(norm, combined_low)
    for cid in sorted(canon_unique) + sorted(canon_places):
        if cid not in entities and len(entities) < 10:
            entities.append(cid)

    # 1c. Specific Chinese Hanzi anchors (suspect names / location-case anchors)
    for hz in _extract_hanzi_anchors_cached(combined):
        if hz not in entities and len(entities) < 10:
            entities.append(hz)

    # 2. Extract numbered timeframes and measurements
    metric_matches = _METRIC_MATCH_RE.findall(combined)
    for mm in metric_matches:
        mm_clean = mm.strip()
        if mm_clean and mm_clean not in keywords:
            keywords.append(mm_clean)

    # 3. Extract proper Hangul word blocks & clean Vietnamese capitalized proper names
    hangul_entities = _HANGUL_ENTITY_RE.findall(combined)
    for he in hangul_entities:
        if he.lower() not in GENERIC_STOPWORDS and he not in entities and len(he) >= 3 and len(entities) < 10:
            entities.append(he)

    vn_caps = _VN_PROPER_NOUN_RE.findall(combined)
    for vc in vn_caps:
        vc_low = vc.lower().strip()
        if (
            vc_low not in GENERIC_STOPWORDS
            and "vụ án" not in vc_low
            and "trung quốc" not in vc_low
            and "hồ sơ" not in vc_low
            and vc not in entities
            and len(entities) < 10
        ):
            entities.append(vc)

    return tuple(entities[:10]), tuple(keywords[:12])


def extract_case_anchors_and_entities(
    title: str, topic: str = "", notes: str = ""
) -> tuple[list[str], list[str]]:
    """
    Extract core entities and subject keywords from title, topic, and notes.
    """
    ents, kws = _extract_case_anchors_and_entities_cached(title or "", topic or "", notes or "")
    return list(ents), list(kws)


def check_case_similarity(
    candidate_text: str,
    target_title: str,
    target_topic: str = "",
    target_entities: list[str] | None = None,
    target_keywords: list[str] | None = None,
) -> tuple[bool, str, float]:
    """
    Determine if candidate_text refers to the same underlying documentary case / topic
    as target_title / target_topic / entities.
    Returns: (is_duplicate: bool, reason: str, confidence: float)
    """
    cand_norm = _normalize_text(candidate_text)
    t_title_norm = _normalize_text(target_title)
    t_topic_norm = _normalize_text(target_topic)
    target_combined = f"{t_title_norm} {t_topic_norm}".strip()
    target_raw = f"{target_title} {target_topic}".strip()

    if not cand_norm or not target_combined:
        return False, "", 0.0

    # 1. Exact or near-exact string match
    if cand_norm == t_title_norm or (len(cand_norm) >= 12 and (cand_norm in t_title_norm or t_title_norm in cand_norm)):
        return True, "Trùng khớp nguyên văn tiêu đề đề tài", 1.0

    # 1b. Specific Chinese Hanzi case/suspect anchor overlap
    cand_hanzi = set(_extract_hanzi_anchors_cached(candidate_text))
    target_hanzi = set(_extract_hanzi_anchors_cached(target_raw))
    if cand_hanzi and target_hanzi:
        shared_hanzi = [h for h in cand_hanzi.intersection(target_hanzi) if len(h) >= 2]
        if any(len(h) >= 3 for h in shared_hanzi) or len(shared_hanzi) >= 2:
            return True, f"Trùng khớp mỏ neo hồ sơ gốc tiếng Trung ({', '.join(shared_hanzi[:3])})", 0.96

    # 1c. Canonical Sino-Korean (한자음) <-> Mandarin (원음) suspect / organization identity match
    cand_low = candidate_text.lower()
    target_raw_low = target_raw.lower()
    cand_u_frozen, cand_p_frozen = _extract_canonical_alias_ids_cached(cand_norm, cand_low)
    targ_u_frozen, targ_p_frozen = _extract_canonical_alias_ids_cached(target_combined, target_raw_low)
    cand_unique_ids = set(cand_u_frozen)
    cand_place_ids = set(cand_p_frozen)
    targ_unique_ids = set(targ_u_frozen)
    targ_place_ids = set(targ_p_frozen)
    for e in (target_entities or []):
        if isinstance(e, str) and e.startswith("person_"):
            targ_unique_ids.add(e)
        elif isinstance(e, str) and e.startswith("org_"):
            targ_unique_ids.add(e)
        elif isinstance(e, str) and e.startswith("place_"):
            targ_place_ids.add(e)

    shared_unique_ids = cand_unique_ids.intersection(targ_unique_ids)
    if shared_unique_ids:
        return (
            True,
            f"Trùng khớp nhân vật/tổ chức hồ sơ gốc xuyên phiên âm ({', '.join(sorted(shared_unique_ids)[:2])})",
            0.96,
        )

    # 2. Cluster anchor match (trilingual + Sino-Korean/Mandarin case resolution)
    for pc in _PREPARED_CASE_CLUSTERS:
        cand_has_marker = any(
            (m_norm and m_norm in cand_norm) or m_low in cand_low
            for _, m_norm, m_low in pc["markers_pairs"]
        )
        cand_has_scen_a = any(sa_norm in cand_norm for _, sa_norm in pc["scen_a_pairs"])
        cand_has_scen_b = any(sb_norm in cand_norm for _, sb_norm in pc["scen_b_pairs"])
        cand_matches_cluster = cand_has_marker or (cand_has_scen_a and cand_has_scen_b)
        if not cand_matches_cluster:
            continue

        target_has_marker = any(
            (m_norm and m_norm in target_combined) or m_low in target_raw_low
            for _, m_norm, m_low in pc["markers_pairs"]
        )
        target_has_scen_a = any(sa_norm in target_combined for _, sa_norm in pc["scen_a_pairs"])
        target_has_scen_b = any(sb_norm in target_combined for _, sb_norm in pc["scen_b_pairs"])
        target_matches_cluster = target_has_marker or (target_has_scen_a and target_has_scen_b)

        if target_matches_cluster:
            matched_anchors = [
                m for m, m_norm, _ in pc["markers_pairs"]
                if (m_norm and m_norm in cand_norm) or (m_norm and m_norm in target_combined)
            ]
            scen_anchors = [
                s for s, s_norm in pc["scen_a_pairs"] + pc["scen_b_pairs"]
                if s_norm in cand_norm or s_norm in target_combined
            ]
            desc = ", ".join((matched_anchors + scen_anchors)[:4])
            return True, f"Trùng khớp hồ sơ vụ việc '{pc['name']}' (Mỏ neo: {desc})", 0.95

    # 2b. Rare quantitative metric + shared place or specific mechanism token
    cand_metrics = _extract_distinctive_metrics_cached(cand_norm)
    targ_metrics = _extract_distinctive_metrics_cached(target_combined)
    shared_metrics = cand_metrics.intersection(targ_metrics)
    shared_places = cand_place_ids.intersection(targ_place_ids)
    if shared_metrics:
        cand_specific_tokens = {
            w for w in cand_norm.split()
            if len(w) >= 2 and w not in GENERIC_STOPWORDS and not w.isdigit()
        }
        targ_specific_tokens = {
            w for w in target_combined.split()
            if len(w) >= 2 and w not in GENERIC_STOPWORDS and not w.isdigit()
        }
        shared_specific = {
            w for w in cand_specific_tokens.intersection(targ_specific_tokens)
            if not _NUMERIC_UNIT_FULL_RE.fullmatch(w)
            and w not in {"위안", "달러", "은행", "사건", "금고", "수배", "미제"}
        }
        if shared_places or len(shared_specific) >= 1:
            return (
                True,
                f"Trùng khớp con số định lượng đặc thù ({', '.join(sorted(shared_metrics))}) & bối cảnh vụ án",
                0.91,
            )

    # 3. Target entities & keywords overlap (auto-extracted when omitted by caller!)
    auto_t_entities, auto_t_keywords = _extract_case_anchors_and_entities_cached(target_title or "", target_topic or "")
    raw_t_entities = list(dict.fromkeys(list(target_entities or []) + list(auto_t_entities)))
    raw_t_keywords = list(dict.fromkeys(list(target_keywords or []) + list(auto_t_keywords)))

    def _clean_anchor_list(items: list[str]) -> list[str]:
        cleaned_list: list[str] = []
        for item in items:
            s = _normalize_text(str(item or ""))
            if not s or len(s) < 2 or s in GENERIC_STOPWORDS:
                continue
            if s.startswith(("person_", "org_", "place_")):
                continue
            if _ANCHOR_NUM_FULL_RE.fullmatch(s):
                continue
            if "vụ án" in s or "vụ lừa đảo" in s or "trung quốc" in s or "hồ sơ" in s:
                continue
            if s not in cleaned_list:
                cleaned_list.append(s)
        return cleaned_list

    t_entities = _clean_anchor_list(raw_t_entities)
    t_keywords = _clean_anchor_list(raw_t_keywords)

    place_variant_tokens = {
        v_norm
        for _, is_place, v_norms in _PREPARED_CANONICAL_ALIASES
        if is_place
        for v_norm in v_norms
    }
    matched_entities = [
        e for e in t_entities
        if len(e) >= 3 and e in cand_norm and e not in place_variant_tokens
    ]
    # Count shared canonical place IDs at most once as a single place match
    if shared_places:
        matched_entities.append(sorted(shared_places)[0])
    matched_keywords = [k for k in t_keywords if len(k) >= 3 and k in cand_norm and k not in matched_entities]

    if len(matched_entities) >= 2 and len(matched_keywords) >= 1:
        return (
            True,
            f"Trùng khớp thực thể cốt lõi ({len(matched_entities)} entities) & từ khóa vụ án ({len(matched_keywords)} keywords)",
            0.90,
        )
    if len(matched_entities) >= 3:
        return True, "Trùng khớp 3 thực thể định danh chính của đề tài", 0.88

    # 4. Token Jaccard overlap (excluding generic stopwords)
    words_cand = [w for w in cand_norm.split() if len(w) >= 2 and w not in GENERIC_STOPWORDS]
    words_target = [w for w in target_combined.split() if len(w) >= 2 and w not in GENERIC_STOPWORDS]
    if words_cand and words_target:
        set_cand = set(words_cand)
        set_target = set(words_target)
        intersection = set_cand.intersection(set_target)
        union = set_cand.union(set_target)
        jaccard = len(intersection) / len(union) if union else 0.0

        if jaccard >= 0.36 and len(intersection) >= 4:
            matched_terms = list(intersection)[:5]
            return True, f"Trùng lặp cấu trúc từ khóa chuyên biệt: {', '.join(matched_terms)}", jaccard

    return False, "", 0.0


def is_duplicate_case(text_a: str, text_b: str) -> bool:
    """Helper shortcut returning boolean."""
    is_dup, _, _ = check_case_similarity(text_a, text_b)
    return is_dup


# ==============================================================================
# CROSS-CASE VENUE & MODUS OPERANDI (MO) COOLDOWN CLUSTERS
# Prevents back-to-back scheduling of TWO DIFFERENT historical suspects who
# struck the exact same landmark venue, used the same weapon/forensic ballistics
# motif, or were arrested via the same bedroom-wardrobe / plainclothes lure setup.
# ==============================================================================

SHARED_VENUE_AND_MO_COOLDOWN_CLUSTERS: list[dict[str, Any]] = [
    {
        "cluster_id": "urumqi_bianjiang_market_ballistics_wardrobe",
        "label": "Cụm bối cảnh Chợ đổi tiền Khách sạn Biên Cương Urumqi (Tân Cương) + Súng 54식/81식 + Soi kính hiển vi kim hỏa/khương tuyến vỏ đạn + Giấu súng tủ quần áo phòng ngủ & Dụ bắt tay không (Bạch Bảo Sơn <-> Mã Hán Khánh)",
        "person_ids": {"person_bai_baoshan", "person_ma_hanqing"},
        "venue_and_mo_markers": (
            "변장빈관", "볜장 빈관", "볜장빈관", "비엔장 상장", "변강빈관", "边疆宾馆",
            "우루무치 환전", "외환 시장", "환전 시장", "환전상", "chợ đổi tiền", "khách sạn biên cương",
            "오사식 권총", "54식 권총", "공이치기 자국", "강선 흔적", "안방 장롱", "안방 옷장",
            "우루무치시 중급인민법원", "우루무치 중급인민법원",
        ),
        "differentiation_directive_ko": (
            "직전 업로드 영상(마한칭 사건)과 '우루무치 변장빈관(볜장 빈관) 환전 시장 습격 · 54식 권총 탄피 공이치기/강선 현미경 대조 · 안방 옷장 총기 은닉 및 비무장 유인 체포 · 우루무치 법원 사형 선고' 배경이 70% 겹치므로 연속 편성을 금지합니다. "
            "바이바오산(백보산) 사건을 제작할 때는 반드시 우루무치 변장빈관 오프닝(Cold Open)을 전면 삭제하고, 바이바오산만의 독보적 시그니처인 '1996년 수도 베이징 스징산 화력발전소·기갑부대 군 초소 3곳 및 방범 순찰차 연쇄 기습을 통한 군용 반자동/자동소총 사냥'으로 1막 오프닝을 시작해야 합니다."
        ),
    },
    {
        "cluster_id": "zhengzhou_1999_125_cooperative_bank_heist",
        "label": "Cụm bối cảnh Vụ cướp đập kính chống đạn Ngân hàng Hợp tác Trịnh Châu 12·5 năm 1999 (Trương Thư Hải <-> Thạch Nhị Quần)",
        "person_ids": {"person_zhang_shuhai", "person_shi_erqun"},
        "venue_and_mo_markers": (
            "정저우 12 5", "정저우 은행 방탄유리", "208만 위안", "郑州12·5", "郑州合作银行",
        ),
        "differentiation_directive_ko": (
            "두 사건 모두 1999년 12월 5일 정저우 합작은행 방탄유리 파쇄 208만 위안 강탈 사건을 다루므로 연속 편성을 금지합니다."
        ),
    },
]


def check_cross_case_mo_collision(
    candidate_text: str,
    recent_records: list[dict[str, Any]] | None,
    *,
    cooldown_window: int = 10,
) -> tuple[bool, str, str]:
    """
    Detect whether `candidate_text` (even if a DIFFERENT suspect) collides heavily in
    crime venue, forensic ballistics motif, or arrest setup with any of the most recent
    `cooldown_window` episodes on the channel.
    Returns `(is_colliding, reason_vi, differentiation_directive_ko)`.
    """
    if not candidate_text or not recent_records:
        return False, "", ""

    cand_norm = _normalize_text(candidate_text)
    cand_low = candidate_text.lower()
    cand_u_ids, _ = _extract_canonical_alias_ids_cached(cand_norm, cand_low)
    recent_slice = list(recent_records)[: max(1, int(cooldown_window))]

    for cluster in SHARED_VENUE_AND_MO_COOLDOWN_CLUSTERS:
        c_persons: set[str] = set(cluster["person_ids"])
        markers: tuple[str, ...] = tuple(cluster["venue_and_mo_markers"])
        cand_in_cluster = bool(cand_u_ids.intersection(c_persons)) or any(
            (_normalize_text(m) and _normalize_text(m) in cand_norm) or (m.lower() in cand_low)
            for m in markers
        )
        if not cand_in_cluster:
            continue

        for rec in recent_slice:
            r_blob = " ".join(
                filter(
                    None,
                    [
                        str(rec.get("title") or ""),
                        str(rec.get("topic") or ""),
                        str(rec.get("case_real_name_zh") or ""),
                        str(rec.get("note") or ""),
                        " ".join(str(x) for x in (rec.get("tags") or [])),
                        " ".join(str(x) for x in (rec.get("anchors") or [])),
                    ],
                )
            ).strip()
            if not r_blob:
                continue
            r_norm = _normalize_text(r_blob)
            r_low = r_blob.lower()
            r_u_ids, _ = _extract_canonical_alias_ids_cached(r_norm, r_low)
            rec_in_cluster = bool(r_u_ids.intersection(c_persons)) or any(
                (_normalize_text(m) and _normalize_text(m) in r_norm) or (m.lower() in r_low)
                for m in markers
            )
            if rec_in_cluster:
                rec_title = str(rec.get("title") or rec.get("case_real_name_zh") or "video gần đây").strip()
                return (
                    True,
                    f"Trùng lặp 70% bối cảnh/thủ đoạn trong cửa sổ Cooldown ({cluster['label']}) với tập vừa đăng: '{rec_title[:80]}'",
                    str(cluster.get("differentiation_directive_ko") or ""),
                )

    return False, "", ""


_VAULT_SAFE_CASH_HEIST_STREAM1_MARKERS: tuple[str, ...] = (
    # Korean: vault break-in, safe-cracking, bank heist, armored cash transport, gold/jewelry/museum treasure vault heist
    "금고 털이", "금고 절단", "금고 개방", "금고 문", "대형 금고", "기업 금고", "은행 금고", "금고 도난",
    "청진기 하나로 다이얼", "산소절단기", "현금수송차", "현금 수송차", "수송차 탈취", "수송차 털",
    "수송차 습격", "장갑 수송차", "은행 장갑차", "현금 3,500만", "현금 3500만", "은행 털", "은행을 털",
    "은행 방탄유리", "은행 강탈", "은행 습격", "저축소", "보석상", "순금 48kg", "순금 괴", "금괴 강탈",
    "선양 3·8", "고궁박물원", "카이펑 박물관", "쓰촨 박물관", "황실 국보 69점", "황실 보물 9점", "1급 국보", "도굴 대사건",
    # Vietnamese: đột nhập kho bạc / mở két / cướp tiền / cướp ngân hàng / xe chở tiền / trộm báu vật
    "đột nhập kho bạc", "trộm kho bạc", "mở két", "phá két", "cắt két", "trộm két", "vét sạch két",
    "két sắt ngân hàng", "cướp tiền", "cướp ngân hàng", "cướp xe chở tiền", "xe bọc thép chở",
    "tài xế xe chở tiền", "đội trưởng xe chở tiền", "cướp tiệm vàng", "cướp 48kg vàng",
    "trộm tử cấm thành", "bảo tàng khai phong", "bảo tàng cố cung", "trộm cổ vật", "đào trộm mộ cổ",
    # Chinese: 金库 / 保险柜 / 运钞车 / 银行劫案 / 储蓄所 / 黄金大案 / 珠宝行 / 博物馆被盗
    "金库被盗", "切割金库", "开启金库", "技术开启", "金库保险柜", "运钞车", "抢劫运钞车",
    "劫持3500万", "银行劫案", "合作银行特大", "建行关山一路", "储蓄所", "绿洲珠宝行", "48公斤黄金", "特大黄金案",
    "沈阳3·8", "故宫博物院", "开封博物馆", "馆藏一级文物被盗", "盗掘古墓葬",
)


def classify_true_crime_topic_stream(item_or_text: dict[str, Any] | str) -> str:
    """
    Classify a True Crime documentary candidate into one of the 2 canonical DNA streams:
      - 'financial_crime' (Luồng 1): Tội phạm Tài chính, Ngân hàng, Kho bạc, Mở két, Cướp tiền/Xe chở tiền & Đào tẩu
      - 'major_violent_crime' (Luồng 2): Trọng án Hình sự, Mất tích Bí ẩn, Án lạnh Pháp y & Truy nã Cấp A Vỏ bọc Hai mặt
    """
    explicit = ""
    if isinstance(item_or_text, dict):
        explicit = str(item_or_text.get("topic_stream") or item_or_text.get("stream_id") or "").strip().lower()
        blob = " ".join([
            str(item_or_text.get("title") or ""),
            str(item_or_text.get("title_target") or ""),
            str(item_or_text.get("title_vi") or ""),
            str(item_or_text.get("winner_cluster") or ""),
            str(item_or_text.get("codex_angle") or ""),
            str(item_or_text.get("case_real_name_zh") or ""),
            str(item_or_text.get("note") or ""),
        ]).lower()
    else:
        blob = str(item_or_text or "").lower()

    # Hard rule: ALL vault break-ins, safe-cracking, bank robberies & cash-in-transit heists belong 100% to Stream 1
    if any(m in blob for m in _VAULT_SAFE_CASH_HEIST_STREAM1_MARKERS):
        return "financial_crime"

    if explicit in {"financial_crime", "finance_crime", "economic_crime"}:
        return "financial_crime"
    if explicit in {"major_violent_crime", "dangerous_crime", "violent_crime", "class_a_fugitive"}:
        return "major_violent_crime"

    violent_strong = (
        "연쇄 미제", "강력사건", "유괴", "납치", "실종", "정화조", "기숙사", "탈옥", "교도소 담장",
        "법의학", "dna", "y-염색체", "미제사건", "1급 수배범", "a급 수배범", "재심 무죄", "누명",
        "trọng án", "bắt cóc", "mất tích", "pháp y", "adn", "án lạnh", "vượt ngục", "minh oan",
        "命案", "积案", "悬案", "绑架", "失踪", "越狱", "法医", "冤案",
    )
    financial_strong = (
        "금융", "국채", "증권", "증권사", "은행", "금고", "횡령", "공금", "사기",
        "다단계", "폰지", "비트코인", "자금 세탁", "환치기", "어음", "신용장", "주가조작",
        "선물거래", "노후 자금", "투자 사기", "펀드", "신탁", "예금 증발", "밀수", "세관", "현금",
        "tài chính", "chứng khoán", "công trái", "kho bạc", "két sắt", "biển thủ", "rửa tiền",
        "lừa đảo", "ponzi", "tín thác", "hối phiếu", "sổ tiết kiệm", "buôn lậu", "thuế",
        "挪用公款", "金融", "国债", "证券", "期货", "非法集资", "骗贷", "票据诈骗", "金库", "猎狐", "走私",
    )
    fin_hits = sum(1 for k in financial_strong if k in blob)
    vio_hits = sum(1 for k in violent_strong if k in blob)
    if fin_hits > vio_hits and fin_hits >= 1:
        return "financial_crime"
    return "major_violent_crime"
