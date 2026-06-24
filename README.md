# 中文指代消解与句子改写系统

这是一个面向期末作业的中文 NLP 项目原型。系统输入中文文本后，会识别代词、候选先行实体，预测指代关系，并生成更明确的改写文本。

## 当前功能

- 规则版代词识别
- 规则版候选实体抽取
- HanLP / LTP 可选增强接口
- 指代关系打分
- 文本改写
- Streamlit 可视化页面
- 新闻/公告长文本模式
- demo/dev/test/真实语料数据集划分
- Accuracy、Precision、Recall、F1 评估
- 错误样本与错误类型分析

## 安装依赖

```bash
pip install -r requirements.txt
```

当前默认版本不强制安装 HanLP 或 LTP。页面中可以选择 HanLP / LTP 增强接口；如果本机未安装对应库，系统会提示并回退到规则版 baseline。

可选模型后端：

```bash
pip install hanlp ltp
```

项目会自动读取根目录 `.env`。当前默认配置为：

```text
HANLP_MODEL=default
LTP_MODEL=LTP/small
```

其中 `HANLP_MODEL=default` 会在程序中映射为 HanLP 的中文多任务模型；`LTP_MODEL=LTP/small` 使用新版 LTP 的小模型。若暂时不安装 HanLP/LTP，也可以保留该配置，系统会自动回退到规则版 baseline。

## 运行 Demo

```bash
streamlit run app.py
```

如果遇到 `server.port does not work when global.developmentMode is true`，可以使用：

```bash
streamlit run app.py --global.developmentMode false
```

单文本分析页支持两种处理模式：

- `通用短文本`：适合单句或短段落，直接进行候选抽取、规则打分和改写。
- `新闻/公告长文本`：将文本切分为标题、段落和句子，使用标题实体、前文实体记忆和局部句子窗口处理“该公司、其、该院”等长文本指代。

## 项目结构

```text
.
├── app.py
├── data/
│   ├── annotation_guideline.md
│   ├── demo.json
│   ├── dev.json
│   ├── real_corpus.json
│   ├── samples.json
│   └── test.json
├── src/
│   ├── evaluator.py
│   ├── mention_extractor.py
│   ├── mention_extractor_types.py
│   ├── nlp_backend.py
│   ├── preprocess.py
│   ├── resolver.py
│   └── rewriter.py
├── reports/
├── outputs/
├── requirements.txt
└── README.md
```

## 数据集

- `demo.json`：10 条，用于页面示例。
- `dev.json`：50 条，用于规则调试。
- `test.json`：60 条，用于最终评估。
- `real_corpus.json`：40 条，更接近新闻、校园、企业场景的真实语料风格样本。
- `samples.json`：120 条完整构造样本备份。
- `new_set.json`：可选的新标注样本，放入 `data/` 后可继续接入训练。
- `train.json`：可选的训练集，由新标注样本合并生成。
- `clue_wsc.json`：可选公开数据集，由 CLUEWSC2020 转换得到，用于公开数据评估。

接入新标注数据：

```bash
python scripts/prepare_training_data.py
```

如果 `data/new_set.json` 缺少 `rewrite` 字段，脚本会根据 `coreference` 自动补出改写文本，并合并生成 `data/train.json`。当前项目采用规则增强路线，这里的“训练”指把新标注样本并入运行时词表，而不是训练神经网络参数。

接入 CLUEWSC2020：

```bash
python scripts/convert_clue_wsc.py --source-dir C:\Users\30657\Desktop\CLUE-master\baselines\models_pytorch\classifier_pytorch\CLUEdatasets\wsc --split train
```

脚本会将 `label=true` 的候选关系转换为本项目的 `pronoun -> antecedent` 格式，输出：

```text
data/clue_wsc.json
reports/clue_wsc_conversion.md
```

`label=false` 的候选关系会保留在 `negative_candidates` 字段中，不参与当前 F1 计算。

将 CLUEWSC2020 作为训练增强集接入：

```bash
python scripts/train_with_clue_wsc.py
```

该脚本会固定切分公开集，生成：

```text
data/clue_wsc_train.json
data/clue_wsc_dev.json
data/train_with_clue_wsc.json
reports/clue_wsc_training_report.md
```

说明：当前项目是规则驱动系统，这里的“训练”指把公开集中的标注实体和代词并入运行时词表，用于增强候选实体覆盖；不是训练 BERT 一类的神经网络参数。

## 示例

```text
输入：小明把书给了小红，因为她需要它。
输出关系：她 -> 小红，它 -> 书
改写：小明把书给了小红，因为小红需要书。
```

## 评估指标

页面中的“数据集评估”标签页可以查看：

- Accuracy
- Precision
- Recall
- F1
- 错误类型
- 漏判关系
- 误判关系

当前规则版 baseline 在构造数据集上表现稳定，在真实语料风格数据集上会暴露更多错误，适合用于报告中的错误分析。

## 消融实验

项目新增规则消融实验，用于分析不同规则信号对最终效果的贡献：

```bash
python scripts/run_ablation.py
```

运行后会生成：

```text
reports/ablation_results.md
```

Streamlit 页面中也提供了“消融实验”标签页，可以直接查看完整规则、去掉距离规则、去掉类型规则等不同配置的结果。

## 模型对比实验

项目支持规则版 baseline、HanLP 和 LTP/legacy 三种后端对比。运行：

```bash
python scripts/run_backend_comparison.py
```

运行后会生成：

```text
reports/backend_comparison.md
reports/backend_comparison.json
```

如果 HanLP/LTP 未安装或模型路径未配置，结果表会显示 `fallback`，表示该后端自动回退到规则版 baseline。安装并配置模型后，重新运行脚本即可得到真实后端对比结果。

当前实验结论：

- 构造测试集上，类型规则最关键。
- 真实语料风格数据集上，距离规则影响最大。
- 性别规则在当前数据中影响较小，后续可以继续增加性别歧义样本。
- BERT / sentence-transformers 可作为下一步语义匹配增强方向。

## 远程部署

如果需要部署到云服务器并通过域名访问，可以参考：

[DEPLOYMENT.md](DEPLOYMENT.md)
