"""名人名字生成器 - 根据人格分配名人名字"""
import random
from typing import Optional


# 名人名字库 - 按性格分类
# 格式：(名字，简短描述/头衔)
CELEBRITY_NAMES = {
    # === 真诚型 - 正直、诚实的历史人物 ===
    "honest": [
        ("诸葛亮", "智慧的化身，鞠躬尽瘁"),
        ("包拯", "铁面无私的包青天"),
        ("海瑞", "刚正不阿的清官"),
        ("林肯", "诚实的阿伯，美国最伟大的总统之一"),
        ("苏格拉底", "追求真理的哲学家"),
        ("华盛顿", "美国国父，诚实砍樱桃树"),
        ("司马光", "砸缸救人的诚实少年"),
        ("季布", "一诺千金的典故主角"),
    ],
    
    # === 爱撒谎型 - 狡诈、善变的历史人物 ===
    "liar": [
        ("曹操", "宁教我负天下人的奸雄"),
        ("司马懿", "装病骗曹爽的隐忍大师"),
        ("路易十一", "法兰西的蜘蛛，狡诈之王"),
        ("俾斯麦", "铁血宰相，权谋大师"),
        ("马基雅维利", "君王论作者，权术代言人"),
        ("陈平", "六出奇计的汉初谋士"),
        ("贾诩", "毒士，算无遗策"),
        ("基辛格", "秘密外交大师"),
    ],
    
    # === 笑面虎型 - 表面温和实则狠辣 ===
    "smooth": [
        ("王莽", "谦恭下士的篡位者"),
        ("袁世凯", "两面三刀的权臣"),
        ("凯瑟琳二世", "开明专制的俄国女皇"),
        ("梅特涅", "欧洲宰相，微笑的阴谋家"),
        ("李林甫", "口蜜腹剑的唐朝宰相"),
        ("塔列朗", "不倒翁，外交变色龙"),
        ("和珅", "乾隆面前的乖臣，背地贪腐"),
        ("克林顿", "微笑的政治家"),
    ],
    
    # === 高冷型 - 话少、神秘、强大 ===
    "cold": [
        ("嬴政", "千古一帝，寡人"),
        ("拿破仑", "沉默的科西嘉怪物"),
        ("斯大林", "钢铁之人，深不可测"),
        ("李小龙", "人狠话不多的武术宗师"),
        ("特斯拉", "孤独的天才发明家"),
        ("康德", "一生未出哥尼斯堡的哲学家"),
        ("牛顿", "孤僻的科学巨人"),
        ("兰卡斯特", "沉默的杀手"),
    ],
    
    # === 啰嗦型 - 话多、分析狂 ===
    "chatterbox": [
        ("苏秦", "合纵六国，滔滔不绝"),
        ("张仪", "连横破纵，能说会道"),
        ("丘吉尔", "演讲大师，喋喋不休"),
        ("马克·吐温", "幽默话痨作家"),
        ("鲁迅", "杂文犀利，针砭时弊"),
        ("伏尔泰", "笔耕不辍的启蒙思想家"),
        ("萧伯纳", "毒舌剧作家"),
        ("李敖", "台湾第一话痨"),
    ],
    
    # === 激进型 - 强势、咄咄逼人 ===
    "aggressive": [
        ("项羽", "力拔山兮气盖世的霸王"),
        ("巴顿", "铁血将军，脾气火爆"),
        ("撒切尔", "铁娘子，绝不妥协"),
        ("朱元璋", "从乞丐到皇帝的狠人"),
        ("彼得大帝", "强势改革的沙皇"),
        ("卡斯特罗", "古巴硬汉"),
        ("张飞", "当阳桥上一声吼"),
        ("李逵", "黑旋风，杀人不眨眼"),
    ],
    
    # === 佛系型 - 低调、随和、与世无争 ===
    "passive": [
        ("老子", "无为而治的道家始祖"),
        ("陶渊明", "采菊东篱下的隐士"),
        ("梭罗", "瓦尔登湖的隐士"),
        ("甘地", "非暴力不合作的圣雄"),
        ("庄子", "逍遥游的哲学家"),
        ("王维", "诗佛，禅意人生"),
        ("孟浩然", "山水田园诗人"),
        ("泰戈尔", "平和的印度诗人"),
    ],
}

# 备用通用名人（当人格不在上述分类时）
GENERAL_NAMES = [
    ("李白", "诗仙，豪放不羁"),
    ("杜甫", "诗圣，忧国忧民"),
    ("苏轼", "大文豪，豁达乐观"),
    ("达芬奇", "文艺复兴全才"),
    ("爱因斯坦", "相对论之父"),
    ("居里夫人", "两获诺奖的科学家"),
    ("拿破仑", "法兰西第一帝国皇帝"),
    ("成吉思汗", "一代天骄，草原霸主"),
    ("亚历山大", "征服世界的马其顿王"),
    ("凯撒", "我来我见我征服"),
    ("埃及艳后", "魅力无双的女王"),
    ("武则天", "中国唯一女皇帝"),
    ("秦始皇", "千古一帝"),
    ("刘邦", "流氓皇帝"),
    ("刘备", "仁德之君"),
]


class NameGenerator:
    """名字生成器"""
    
    def __init__(self):
        self.used_names: set[str] = set()  # 已使用的名字
        self.player_names: dict[int, str] = {}  # 玩家 ID 到名字的映射
    
    def get_name_for_personality(self, personality_key: str) -> str:
        """
        根据人格获取一个名人名字
        
        Args:
            personality_key: 人格关键词（如 honest, liar, smooth 等）
            
        Returns:
            名人名字（不含描述）
        """
        # 获取该人格对应的名字列表
        names_list = CELEBRITY_NAMES.get(personality_key, GENERAL_NAMES)
        
        # 过滤掉已使用的名字
        available = [(name, desc) for name, desc in names_list if name not in self.used_names]
        
        if not available:
            # 如果该人格的名字都用完了，从通用名字中选
            available = [(name, desc) for name, desc in GENERAL_NAMES if name not in self.used_names]
        
        if not available:
            # 所有名字都用完了，随机生成一个编号名字
            return f"神秘人{random.randint(1, 99)}"
        
        # 随机选择一个
        selected = random.choice(available)
        self.used_names.add(selected[0])
        
        return selected[0]
    
    def get_name_with_description(self, personality_key: str) -> tuple[str, str]:
        """
        根据人格获取名人名字和描述
        
        Args:
            personality_key: 人格关键词
            
        Returns:
            (名字，描述) 元组
        """
        names_list = CELEBRITY_NAMES.get(personality_key, GENERAL_NAMES)
        
        available = [(name, desc) for name, desc in names_list if name not in self.used_names]
        
        if not available:
            available = [(name, desc) for name, desc in GENERAL_NAMES if name not in self.used_names]
        
        if not available:
            return f"神秘人{random.randint(1, 99)}", "身份成谜"
        
        selected = random.choice(available)
        self.used_names.add(selected[0])
        
        return selected
    
    def assign_name_to_player(self, player_id: int, personality_key: str) -> str:
        """
        为玩家分配名字
        
        Args:
            player_id: 玩家 ID
            personality_key: 人格关键词
            
        Returns:
            分配的名字
        """
        if player_id in self.player_names:
            return self.player_names[player_id]
        
        name = self.get_name_for_personality(personality_key)
        self.player_names[player_id] = name
        return name
    
    def get_player_name(self, player_id: int) -> Optional[str]:
        """获取玩家名字"""
        return self.player_names.get(player_id)
    
    def reset(self) -> None:
        """重置所有已用名字"""
        self.used_names.clear()
        self.player_names.clear()
    
    def get_all_assigned_names(self) -> dict[int, str]:
        """获取所有已分配的名字"""
        return self.player_names.copy()
