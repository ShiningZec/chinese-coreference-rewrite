import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";


const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, "..");
const OUTPUT = path.join(ROOT, "outputs", "中文指代消解与句子改写系统_14页汇报PPT.pptx");
const QA_DIR = path.join(ROOT, "outputs", "presentation_qa");

const COLORS = {
  bg: "#f8fafc",
  white: "#ffffff",
  ink: "#0f172a",
  muted: "#475569",
  soft: "#e2e8f0",
  blue: "#2563eb",
  cyan: "#0891b2",
  green: "#16a34a",
  amber: "#d97706",
  red: "#dc2626",
  slate: "#334155",
};

const SLIDE = { width: 1280, height: 720 };
const FRAME = { left: 72, top: 58, width: 1136, height: 604 };


async function loadArtifactTool() {
  try {
    return await import("@oai/artifact-tool");
  } catch {
    const fallback = path.join(
      process.env.USERPROFILE || "",
      ".cache",
      "codex-runtimes",
      "codex-primary-runtime",
      "dependencies",
      "node",
      "node_modules",
      "@oai",
      "artifact-tool",
      "dist",
      "artifact_tool.mjs",
    );
    return await import(pathToFileURL(fallback).href);
  }
}


async function writeBlob(filePath, blob) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}


async function loadJson(relativePath, fallback) {
  try {
    return JSON.parse(await fs.readFile(path.join(ROOT, relativePath), "utf-8"));
  } catch {
    return fallback;
  }
}


function addText(slide, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    fontSize: style.fontSize || 24,
    color: style.color || COLORS.ink,
    bold: style.bold || false,
    alignment: style.alignment || "left",
  };
  return shape;
}


function addBox(slide, position, fill = COLORS.white, line = COLORS.soft) {
  return slide.shapes.add({
    geometry: "roundRect",
    position,
    fill,
    line: { style: "solid", fill: line, width: 1 },
    borderRadius: "rounded-lg",
  });
}


function addSlideTitle(slide, title, eyebrow = "") {
  if (eyebrow) {
    addText(slide, eyebrow, { left: FRAME.left, top: 36, width: 720, height: 28 }, {
      fontSize: 16,
      bold: true,
      color: COLORS.blue,
    });
  }
  addText(slide, title, { left: FRAME.left, top: 70, width: 960, height: 54 }, {
    fontSize: 38,
    bold: true,
    color: COLORS.ink,
  });
}


function addFooter(slide, pageNumber) {
  addText(slide, `中文指代消解与句子改写系统  ·  ${pageNumber}/14`, {
    left: 72,
    top: 676,
    width: 540,
    height: 24,
  }, { fontSize: 14, color: "#94a3b8" });
}


function addBullets(slide, items, position, options = {}) {
  const text = items.map((item) => `• ${item}`).join("\n");
  return addText(slide, text, position, {
    fontSize: options.fontSize || 23,
    color: options.color || COLORS.slate,
  });
}


function addMetric(slide, label, value, note, position, color = COLORS.blue) {
  addBox(slide, position, COLORS.white, "#cbd5e1");
  addText(slide, value, {
    left: position.left + 22,
    top: position.top + 22,
    width: position.width - 44,
    height: 48,
  }, { fontSize: 34, bold: true, color });
  addText(slide, label, {
    left: position.left + 22,
    top: position.top + 78,
    width: position.width - 44,
    height: 32,
  }, { fontSize: 20, bold: true, color: COLORS.ink });
  addText(slide, note, {
    left: position.left + 22,
    top: position.top + 116,
    width: position.width - 44,
    height: 52,
  }, { fontSize: 16, color: COLORS.muted });
}


function addChip(slide, label, left, top, width, color) {
  addBox(slide, { left, top, width, height: 44 }, "#eff6ff", color);
  addText(slide, label, { left: left + 14, top: top + 10, width: width - 28, height: 24 }, {
    fontSize: 18,
    bold: true,
    color,
    alignment: "center",
  });
}


function addProcess(slide, steps, top) {
  const width = 208;
  const gap = 24;
  steps.forEach((step, index) => {
    const left = FRAME.left + index * (width + gap);
    addBox(slide, { left, top, width, height: 120 }, COLORS.white, "#cbd5e1");
    addText(slide, String(index + 1), { left: left + 18, top: top + 16, width: 34, height: 34 }, {
      fontSize: 24,
      bold: true,
      color: COLORS.blue,
      alignment: "center",
    });
    addText(slide, step.title, { left: left + 56, top: top + 18, width: width - 70, height: 28 }, {
      fontSize: 20,
      bold: true,
      color: COLORS.ink,
    });
    addText(slide, step.body, { left: left + 20, top: top + 58, width: width - 40, height: 46 }, {
      fontSize: 16,
      color: COLORS.muted,
    });
    if (index < steps.length - 1) {
      addText(slide, "→", { left: left + width + 2, top: top + 42, width: gap + 20, height: 34 }, {
        fontSize: 32,
        bold: true,
        color: COLORS.cyan,
        alignment: "center",
      });
    }
  });
}


function addSimpleTable(slide, headers, rows, position, columnWidths) {
  const rowH = 48;
  addBox(slide, position, COLORS.white, "#cbd5e1");
  let x = position.left;
  headers.forEach((header, i) => {
    addText(slide, header, { left: x + 12, top: position.top + 12, width: columnWidths[i] - 24, height: 24 }, {
      fontSize: 17,
      bold: true,
      color: COLORS.ink,
    });
    x += columnWidths[i];
  });
  rows.forEach((row, r) => {
    const y = position.top + rowH * (r + 1);
    slide.shapes.add({
      geometry: "rect",
      position: { left: position.left + 1, top: y, width: position.width - 2, height: 1 },
      fill: "#e2e8f0",
      line: { style: "solid", fill: "none", width: 0 },
    });
    let cellX = position.left;
    row.forEach((cell, c) => {
      addText(slide, cell, { left: cellX + 12, top: y + 12, width: columnWidths[c] - 24, height: 24 }, {
        fontSize: 16,
        color: c === 0 ? COLORS.ink : COLORS.muted,
        bold: c === 0,
      });
      cellX += columnWidths[c];
    });
  });
}


function setBg(slide) {
  slide.background.fill = COLORS.bg;
}


async function main() {
  const { Presentation, PresentationFile } = await loadArtifactTool();
  const train = await loadJson("data/train.json", []);
  const samples = await loadJson("data/samples.json", []);
  const dev = await loadJson("data/dev.json", []);
  const test = await loadJson("data/test.json", []);
  const real = await loadJson("data/real_corpus.json", []);

  const deck = Presentation.create({ slideSize: SLIDE });

  const slide1 = deck.slides.add();
  setBg(slide1);
  addText(slide1, "中文指代消解与句子改写系统", {
    left: 72,
    top: 120,
    width: 860,
    height: 72,
  }, { fontSize: 52, bold: true });
  addText(slide1, "面向中文文本理解与问答场景的可解释 NLP 期末项目", {
    left: 74,
    top: 212,
    width: 820,
    height: 38,
  }, { fontSize: 26, color: COLORS.muted });
  addMetric(slide1, "新标注样本", `${train.length || 85} 条`, "接入 train.json，用于规则增强与错误分析", {
    left: 72,
    top: 350,
    width: 300,
    height: 178,
  }, COLORS.blue);
  addMetric(slide1, "训练集 F1", "0.8765", "组织指代增强后的训练集表现", {
    left: 404,
    top: 350,
    width: 300,
    height: 178,
  }, COLORS.green);
  addMetric(slide1, "展示方式", "Web Demo", "Streamlit + 云服务器部署", {
    left: 736,
    top: 350,
    width: 300,
    height: 178,
  }, COLORS.cyan);
  addFooter(slide1, 1);

  const slide2 = deck.slides.add();
  setBg(slide2);
  addSlideTitle(slide2, "为什么选择指代消解", "项目背景");
  addBullets(slide2, [
    "中文文本经常省略主语，代词指向依赖上下文。",
    "在问答、摘要、信息抽取中，代词不清会影响理解。",
    "句子改写能把隐含指代显式化，便于展示与评估。",
  ], { left: 92, top: 174, width: 540, height: 230 });
  addBox(slide2, { left: 710, top: 162, width: 420, height: 280 }, "#ecfeff", "#67e8f9");
  addText(slide2, "例子", { left: 744, top: 190, width: 220, height: 34 }, {
    fontSize: 24,
    bold: true,
    color: COLORS.cyan,
  });
  addText(slide2, "马斯克整理了书，\n他准备再次确认它。", {
    left: 744,
    top: 242,
    width: 340,
    height: 86,
  }, { fontSize: 26, color: COLORS.ink });
  addText(slide2, "改写：马斯克准备确认书", {
    left: 744,
    top: 358,
    width: 340,
    height: 32,
  }, { fontSize: 20, bold: true, color: COLORS.green });
  addFooter(slide2, 2);

  const slide3 = deck.slides.add();
  setBg(slide3);
  addSlideTitle(slide3, "任务定义：识别、消解、改写", "核心任务");
  addProcess(slide3, [
    { title: "输入文本", body: "用户输入一句或一段中文" },
    { title: "抽取候选", body: "识别实体、代词和指代表达" },
    { title: "关系打分", body: "结合距离、类型、性别、位置" },
    { title: "文本改写", body: "用先行词替换可消解代词" },
    { title: "可视化", body: "展示高亮、候选得分和错误" },
  ], 220);
  addFooter(slide3, 3);

  const slide4 = deck.slides.add();
  setBg(slide4);
  addSlideTitle(slide4, "技术栈与工程结构", "实现基础");
  addChip(slide4, "Python", 100, 180, 150, COLORS.blue);
  addChip(slide4, "Streamlit", 276, 180, 170, COLORS.green);
  addChip(slide4, "规则引擎", 472, 180, 170, COLORS.cyan);
  addChip(slide4, "HanLP / LTP", 668, 180, 190, COLORS.amber);
  addChip(slide4, "Nginx / 云服务器", 884, 180, 230, COLORS.red);
  addSimpleTable(slide4, ["模块", "职责"], [
    ["mention_extractor.py", "抽取实体与代词，并接入训练词表"],
    ["resolver.py", "候选先行词打分、歧义检测、规则覆盖"],
    ["rewriter.py", "根据消解结果生成改写文本"],
    ["evaluator.py", "计算 Precision / Recall / F1 并输出错误样本"],
    ["app.py", "Streamlit 页面、评估页、消融实验页"],
  ], { left: 126, top: 280, width: 1020, height: 292 }, [330, 690]);
  addFooter(slide4, 4);

  const slide5 = deck.slides.add();
  setBg(slide5);
  addSlideTitle(slide5, "数据集构成", "数据准备");
  slide5.charts.add("bar", {
    position: { left: 120, top: 180, width: 520, height: 330 },
    categories: ["samples", "dev", "test", "real", "train"],
    series: [{ name: "样本数", values: [samples.length || 120, dev.length || 50, test.length || 60, real.length || 40, train.length || 85], fill: COLORS.blue }],
    hasLegend: false,
    dataLabels: { showValue: true, position: "outEnd" },
    yAxis: { majorGridlines: { style: "solid", fill: "#dbeafe", width: 1 } },
  });
  addBullets(slide5, [
    "构造集用于验证基础规则稳定性。",
    "真实语料风格集用于暴露复杂错误。",
    "new_set.json 新增 85 条标注数据，生成 train.json。",
    "训练集包含 162 个真实指代关系。",
  ], { left: 720, top: 190, width: 420, height: 240 }, { fontSize: 21 });
  addFooter(slide5, 5);

  const slide6 = deck.slides.add();
  setBg(slide6);
  addSlideTitle(slide6, "系统架构", "从输入到展示");
  addProcess(slide6, [
    { title: "数据层", body: "demo/dev/test/train JSON" },
    { title: "抽取层", body: "规则词典 + 可选 NLP 后端" },
    { title: "消解层", body: "候选排序与歧义检测" },
    { title: "评估层", body: "指标、错误、消融实验" },
    { title: "展示层", body: "Streamlit Web Demo" },
  ], 190);
  addText(slide6, "设计取向：优先保证可解释性，每个判断都能展示候选得分和规则理由。", {
    left: 160,
    top: 420,
    width: 920,
    height: 48,
  }, { fontSize: 24, bold: true, color: COLORS.slate, alignment: "center" });
  addFooter(slide6, 6);

  const slide7 = deck.slides.add();
  setBg(slide7);
  addSlideTitle(slide7, "规则引擎如何判断先行词", "核心算法");
  addSimpleTable(slide7, ["信号", "含义", "作用"], [
    ["距离", "候选实体与代词的字符距离", "越近通常越可能"],
    ["位置", "候选应优先出现在代词之前", "降低后文实体误判"],
    ["类型", "人称/物体/组织指代匹配", "当前最关键规则"],
    ["性别", "他/她与已知人名性别", "处理基础人名样本"],
    ["角色模式", "替/帮/为、对/向/跟说", "处理动作角色与歧义"],
  ], { left: 98, top: 162, width: 1084, height: 292 }, [160, 470, 454]);
  addText(slide7, "输出不是黑盒标签，而是候选列表、分数和理由。", {
    left: 148,
    top: 510,
    width: 980,
    height: 44,
  }, { fontSize: 25, bold: true, color: COLORS.blue, alignment: "center" });
  addFooter(slide7, 7);

  const slide8 = deck.slides.add();
  setBg(slide8);
  addSlideTitle(slide8, "新标注集接入流程", "训练增强");
  addProcess(slide8, [
    { title: "拉取数据", body: "从 GitHub 获取 data/new_set.json" },
    { title: "补 rewrite", body: "脚本自动根据标注关系改写" },
    { title: "生成 train", body: "输出 data/train.json" },
    { title: "扩展词表", body: "并入 pronoun / antecedent" },
    { title: "重新评估", body: "生成错误分析报告" },
  ], 170);
  addText(slide8, "对应脚本：scripts/prepare_training_data.py 与 scripts/analyze_training_errors.py", {
    left: 118,
    top: 430,
    width: 1040,
    height: 40,
  }, { fontSize: 23, bold: true, color: COLORS.slate, alignment: "center" });
  addFooter(slide8, 8);

  const slide9 = deck.slides.add();
  setBg(slide9);
  addSlideTitle(slide9, "训练集表现提升", "实验结果");
  slide9.charts.add("bar", {
    position: { left: 130, top: 175, width: 500, height: 340 },
    categories: ["接入前", "组织指代增强后"],
    series: [{ name: "F1(%)", values: [79.63, 87.65], fill: COLORS.green }],
    hasLegend: false,
    dataLabels: { showValue: true, position: "outEnd" },
    yAxis: { min: 0, max: 100, majorGridlines: { style: "solid", fill: "#dcfce7", width: 1 } },
  });
  addMetric(slide9, "F1 提升", "+0.0802", "组织指代表达带来主要增益", {
    left: 730,
    top: 178,
    width: 320,
    height: 170,
  }, COLORS.green);
  addMetric(slide9, "错误减少", "34 → 21", "错误样本减少 13 个", {
    left: 730,
    top: 376,
    width: 320,
    height: 170,
  }, COLORS.blue);
  addFooter(slide9, 9);

  const slide10 = deck.slides.add();
  setBg(slide10);
  addSlideTitle(slide10, "错误类型分布", "错误分析");
  slide10.charts.add("bar", {
    position: { left: 110, top: 162, width: 610, height: 390 },
    categories: ["它/它们", "多人物", "组织指代", "过度预测", "称谓", "其他", "我/你"],
    series: [{ name: "错误样本", values: [6, 4, 4, 2, 2, 2, 1], fill: COLORS.blue }],
    hasLegend: false,
    dataLabels: { showValue: true, position: "outEnd" },
    yAxis: { majorGridlines: { style: "solid", fill: "#dbeafe", width: 1 } },
  });
  addBullets(slide10, [
    "最大问题不是单一模型失败，而是多类语言现象混合。",
    "标注粒度不一致会直接影响指标。",
    "多人物同形代词需要位置级评估与语义角色信息。",
  ], { left: 790, top: 190, width: 340, height: 240 }, { fontSize: 21 });
  addFooter(slide10, 10);

  const slide11 = deck.slides.add();
  setBg(slide11);
  addSlideTitle(slide11, "典型错误样本", "案例复盘");
  addSimpleTable(slide11, ["类型", "样本", "问题"], [
    ["多人物", "小美会见小刚，他对她说话", "角色可反转，需语义判断"],
    ["称谓", "孔子问子路，弟子回答老师", "老师/弟子依赖身份知识"],
    ["粒度", "它们 -> 稻穗", "gold 写作“它”，原文为“它们”"],
    ["组织", "该院 -> 博物院", "候选过近导致偏向展品"],
    ["过度预测", "鲁迅写下了它", "上下文没有 gold 指代"],
  ], { left: 86, top: 162, width: 1108, height: 292 }, [150, 520, 438]);
  addFooter(slide11, 11);

  const slide12 = deck.slides.add();
  setBg(slide12);
  addSlideTitle(slide12, "Web Demo 与部署", "成果展示");
  addBullets(slide12, [
    "页面输入一句中文文本，点击开始分析。",
    "展示原文高亮、候选实体、代词、关系表、候选得分。",
    "歧义样本会提示人工确认，并跳过自动改写。",
    "云服务器可通过公网 IP + 8501 临时展示，正式版可接 Nginx。",
  ], { left: 92, top: 170, width: 510, height: 300 });
  addBox(slide12, { left: 690, top: 164, width: 430, height: 300 }, "#f0fdf4", "#86efac");
  addText(slide12, "部署路径", { left: 724, top: 196, width: 200, height: 34 }, {
    fontSize: 26,
    bold: true,
    color: COLORS.green,
  });
  addText(slide12, "GitHub\n→ 云服务器\n→ Streamlit\n→ 浏览器展示", {
    left: 724,
    top: 252,
    width: 340,
    height: 150,
  }, { fontSize: 30, bold: true, color: COLORS.ink, alignment: "center" });
  addFooter(slide12, 12);

  const slide13 = deck.slides.add();
  setBg(slide13);
  addSlideTitle(slide13, "下一步：从规则到语义模型", "进阶方向");
  addSimpleTable(slide13, ["方向", "价值", "实现方式"], [
    ["Span 级评估", "解决同形代词混淆", "记录 pronoun_start / antecedent_start"],
    ["语义相似度", "减少近距离误判", "BERT / sentence-transformers"],
    ["角色识别", "处理“他说/他问/他嘱咐”", "依存句法或事件模板"],
    ["标注规范", "减少它/它们粒度误差", "统一按原文完整 span 标注"],
  ], { left: 88, top: 166, width: 1104, height: 244 }, [220, 380, 504]);
  addText(slide13, "这部分可作为报告中的“进阶改进与未来工作”。", {
    left: 144,
    top: 500,
    width: 960,
    height: 44,
  }, { fontSize: 25, bold: true, color: COLORS.blue, alignment: "center" });
  addFooter(slide13, 13);

  const slide14 = deck.slides.add();
  setBg(slide14);
  addText(slide14, "总结", { left: 72, top: 92, width: 300, height: 70 }, {
    fontSize: 54,
    bold: true,
    color: COLORS.ink,
  });
  addBullets(slide14, [
    "完成了中文指代消解、文本改写、可视化评估与云端展示闭环。",
    "新增 85 条标注数据，并自动生成 rewrite 与 train.json。",
    "通过组织指代增强，训练集 F1 提升到 0.8765。",
    "错误分析揭示了后续 BERT 语义匹配与 span 级评估的必要性。",
  ], { left: 112, top: 210, width: 880, height: 260 }, { fontSize: 25 });
  addText(slide14, "从可解释 baseline 出发，逐步走向更真实的中文语义理解。", {
    left: 112,
    top: 530,
    width: 880,
    height: 42,
  }, { fontSize: 26, bold: true, color: COLORS.green });
  addFooter(slide14, 14);

  await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
  await fs.mkdir(QA_DIR, { recursive: true });

  for (const [index, slide] of deck.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(path.join(QA_DIR, `${stem}.png`), await deck.export({ slide, format: "png", scale: 1 }));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(QA_DIR, `${stem}.layout.json`), await layout.text());
  }

  await writeBlob(path.join(QA_DIR, "deck-montage.webp"), await deck.export({
    format: "webp",
    montage: true,
    scale: 1,
  }));

  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(OUTPUT);

  console.log(`slides: ${deck.slides.items.length}`);
  console.log(`pptx: ${OUTPUT}`);
  console.log(`qa: ${QA_DIR}`);
}


main()
  .then(() => {
    process.exit(0);
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
