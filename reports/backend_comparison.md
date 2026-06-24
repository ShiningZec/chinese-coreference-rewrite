# 基本模型与 HanLP/LTP 对比

| 数据集 | 后端 | 状态 | Precision | Recall | F1 | ΔF1 | 正确/真实 | 说明 |
|---|---|---|---:|---:|---:|---:|---:|---|
| dev | rule_baseline | available | 1.0000 | 1.0000 | 1.0000 | +0.0000 | 100/100 | 使用内置规则抽取。 |
| dev | hanlp | fallback | 1.0000 | 1.0000 | 1.0000 | +0.0000 | 100/100 | HanLP 未启用：No module named 'hanlp' |
| dev | ltp_or_legacy | fallback | 1.0000 | 1.0000 | 1.0000 | +0.0000 | 100/100 | LTP 未启用：modern=No module named 'ltp'；legacy=No module named 'pyltp' |
| test | rule_baseline | available | 0.9667 | 0.9667 | 0.9667 | +0.0000 | 87/90 | 使用内置规则抽取。 |
| test | hanlp | fallback | 0.9667 | 0.9667 | 0.9667 | +0.0000 | 87/90 | HanLP 未启用：No module named 'hanlp' |
| test | ltp_or_legacy | fallback | 0.9667 | 0.9667 | 0.9667 | +0.0000 | 87/90 | LTP 未启用：modern=No module named 'ltp'；legacy=No module named 'pyltp' |
| real_corpus | rule_baseline | available | 0.9565 | 0.9565 | 0.9565 | +0.0000 | 44/46 | 使用内置规则抽取。 |
| real_corpus | hanlp | fallback | 0.9565 | 0.9565 | 0.9565 | +0.0000 | 44/46 | HanLP 未启用：No module named 'hanlp' |
| real_corpus | ltp_or_legacy | fallback | 0.9565 | 0.9565 | 0.9565 | +0.0000 | 44/46 | LTP 未启用：modern=No module named 'ltp'；legacy=No module named 'pyltp' |
| samples | rule_baseline | available | 0.9857 | 0.9857 | 0.9857 | +0.0000 | 207/210 | 使用内置规则抽取。 |
| samples | hanlp | fallback | 0.9857 | 0.9857 | 0.9857 | +0.0000 | 207/210 | HanLP 未启用：No module named 'hanlp' |
| samples | ltp_or_legacy | fallback | 0.9857 | 0.9857 | 0.9857 | +0.0000 | 207/210 | LTP 未启用：modern=No module named 'ltp'；legacy=No module named 'pyltp' |
| train | rule_baseline | available | 0.8765 | 0.8765 | 0.8765 | +0.0000 | 142/162 | 使用内置规则抽取。 |
| train | hanlp | fallback | 0.8765 | 0.8765 | 0.8765 | +0.0000 | 142/162 | HanLP 未启用：No module named 'hanlp' |
| train | ltp_or_legacy | fallback | 0.8765 | 0.8765 | 0.8765 | +0.0000 | 142/162 | LTP 未启用：modern=No module named 'ltp'；legacy=No module named 'pyltp' |
