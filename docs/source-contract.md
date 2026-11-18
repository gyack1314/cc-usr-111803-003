# 来源字段

plant_roster 与 daily_slaughter 的 company_id 是来源声明的关联线索；字段相等不证明两份原文已经完整或同版。

来源目录中的 expected_revision 表示该链接当前要求核实的来源版次；normal.json 为 v1，revised.json 将第一份来源改指同链接 v2。旧版原文仍可用于历史视图。
# 来源契约

`plant_roster.plants` 保存主体 active/merged 状态及 successor 生效日。日公告含逐日企业代码、宰量及 actual/estimate 口径；周汇总的 scope 表示统计周内出现的主体身份。当前聚合在生效日之后将旧代码映射到 successor，estimate 不并入实绩，缺失日或 scope/合计不一致时不能作为完整周报发布。历史视图保留发布时的名录版次。
