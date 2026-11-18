# 屠宰企业开工与日宰量资料接续

项目保存屠宰企业名录、逐日宰量和周度汇总原件。查询会按名录生效日处理合并前后的主体身份，将估算量与实绩分开，并对照当周实际覆盖和汇总范围。名录或周报修订未到齐时不能继续发布旧口径；已发布结果仍保留当时使用的身份范围。合成样例不访问外部站点，来源字段见 docs/source-contract.md。

在项目根目录运行：

    python -m unittest discover -s tests -v
    python -m compileall -q capture_service tests
    python -m capture_service.cli inspect data/normal.json

容器运行：docker build -t pork-collection-003 .；docker run --rm pork-collection-003。
