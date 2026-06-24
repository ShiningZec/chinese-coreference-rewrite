# CLUEWSC2020 转换结果

- 来源文件：`C:\Users\30657\Desktop\CLUE-master\baselines\models_pytorch\classifier_pytorch\CLUEdatasets\wsc\train.json`
- 输出文件：`C:\Users\30657\Documents\Codex\2026-05-26\huggingface-neuralcoref-https-github-com-huggingface\data\clue_wsc.json`
- 原始记录数：1244
- 唯一文本数：387
- 转换样本数：382
- gold 指代关系数：517
- negative candidates：716
- 标签分布：{'false': 727, 'true': 517}

说明：仅将 `label=true` 的候选关系转为本项目的 gold coreference；`label=false` 保留为 negative_candidates，不参与当前 F1 计算。
