# 中文指代消解与句子改写系统

这是一个面向期末作业的中文 NLP 项目原型。系统输入中文文本后，会识别代词、候选先行实体，预测指代关系，并生成更明确的改写文本。

## 当前版本

当前实现的是最小可行版本：

- 规则版代词识别
- 规则版候选实体抽取
- 指代关系打分
- 文本改写
- Streamlit 可视化页面
- 示例数据与基础评估

后续可以继续接入 HanLP、LTP 或 BERT 类模型增强效果。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行 Demo

```bash
streamlit run app.py
```

如果遇到 `server.port does not work when global.developmentMode is true`，可以使用：

```bash
streamlit run app.py --global.developmentMode false
```

## 项目结构

```text
.
├── app.py
├── data/
│   └── samples.json
├── src/
│   ├── evaluator.py
│   ├── mention_extractor.py
│   ├── preprocess.py
│   ├── resolver.py
│   └── rewriter.py
├── IMPLEMENTATION_PLAN.md
├── README.md
└── requirements.txt
```

## 示例

```text
输入：小明把书给了小红，因为她需要它。
输出：小明把书给了小红，因为小红需要书。
```
