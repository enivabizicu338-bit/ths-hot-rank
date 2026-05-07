# 同花顺热榜 · 动态趋势追踪

基于 GitHub Actions 每 30 分钟自动采集同花顺热榜数据，通过 GitHub Pages 展示趋势。

## 功能

- 📊 热门股票排名变化趋势图
- 🔥 实时热榜 TOP 100
- 📈 热门概念板块
- 📋 排名变动详情 + 迷你趋势线
- 🔄 每 30 分钟自动更新

## 部署步骤

1. Fork 此仓库
2. 进入仓库 Settings → Pages → Source 选择 `main` 分支
3. 进入 Settings → Actions → General → 启用 Actions
4. 手动触发一次 Actions（Actions → 采集同花顺热榜数据 → Run workflow）
5. 等待部署完成，访问 `https://<your-username>.github.io/<repo-name>/`

## 数据说明

- 数据来源: 东方财富（通过 akshare）
- 采集频率: 每 30 分钟
- 数据存储: `data/` 目录下的 JSON 文件
- 快照保留: 最近 200 个（约 4 天）
