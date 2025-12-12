import uuid
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Index, UniqueConstraint
from .base import Base

# 技能表
# - 主键 `id` 使用 UUID 字符串
# - `skill_id` 为原始的技能编号（文本解析得到），设置为唯一，用于业务关联与查询
# - `source_span` 存放解析来源位置信息（含 meta/description/special_effects/full_text 的 JSON）
class Skill(Base):
    __tablename__ = "skills"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键UUID")
    skill_id = Column(String, nullable=False, comment="技能编号（原始文本ID，唯一）")
    name = Column(String, nullable=False, comment="技能名称")
    source_span = Column(Text, nullable=False, comment="解析来源信息JSON（含meta/description/special_effects/full_text）")
    __table_args__ = (UniqueConstraint("skill_id", name="uq_skills_skill_id"),)

# 序列表
# - 主键 `id` 使用 UUID 字符串
# - `series_id` 为业务侧的序列标识（如 `<skill_id>:<label>`），设置为唯一
# - `skill_id` 仍外键引用技能表中的 `skill_id`（唯一列），保持现有业务入参不变
class Series(Base):
    __tablename__ = "series"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键UUID")
    series_id = Column(String, nullable=False, comment="序列标识（skill_id:label，唯一）")
    skill_id = Column(String, ForeignKey("skills.skill_id"), nullable=False, comment="关联技能编号（skills.skill_id）")
    label = Column(String, nullable=False, comment="序列标签（规范化）")
    units = Column(String, nullable=False, comment="单位（如 点）")
    meta = Column(Text, comment="序列元数据JSON（预留）")
    __table_args__ = (UniqueConstraint("series_id", name="uq_series_series_id"),)

# 序列值表
# - 主键 `id` 使用 UUID 字符串
# - 每行对应一次级次值（包含差值与跃迁标记）
class Value(Base):
    __tablename__ = "values_tbl"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键UUID")
    series_id = Column(String, ForeignKey("series.series_id"), nullable=False, comment="关联序列标识（series.series_id）")
    level_index = Column(Integer, nullable=False, comment="级次索引（从1开始）")
    value = Column(Float, nullable=False, comment="数值")
    diff_to_prev = Column(Float, comment="与前一级差值")
    is_jump = Column(Integer, nullable=False, comment="是否跃迁点（1/0）")

Index("idx_values_series_level", Value.series_id, Value.level_index)

# 序列分析表
# - 主键 `id` 使用 UUID 字符串
# - `series_id` 作为唯一列便于按业务标识定位分析记录
class Analysis(Base):
    __tablename__ = "analysis"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), comment="主键UUID")
    series_id = Column(String, ForeignKey("series.series_id"), nullable=False, comment="关联序列标识（唯一）")
    is_linear = Column(Integer, nullable=False, comment="是否线性增长（1/0）")
    trend = Column(Text, nullable=False, comment="趋势（increasing/decreasing/mixed）")
    min = Column(Float, comment="最小值")
    max = Column(Float, comment="最大值")
    count = Column(Integer, nullable=False, comment="值数量")
    jump_points = Column(Text, nullable=False, comment="跃迁点索引JSON")
    __table_args__ = (UniqueConstraint("series_id", name="uq_analysis_series_id"),)
