# 移动端创作工作台 - 部署与配置指南

## 一、项目概述

这是一个**单文件 HTML 网页** + **GitHub Actions 自动化**的移动端创作工作台。

- **前端**：一个 `index.html` 文件，部署在 GitHub Pages
- **数据本地**：每日计划、复盘、备忘录存手机浏览器 `localStorage`
- **云端热点**：选题灵感、爆款二创数据存在 GitHub Gist，由 GitHub Actions 每天定时更新
- **自动化**：每天北京时间 8:00 / 14:00 / 20:00 自动采集热点 + AI 改写，推送到 Gist

---

## 二、你需要准备的信息（三样）

根据你的要求，最后明确告诉你需要提供：

### 1. GitHub Token（用于自动化更新 Gist）

**用途**：GitHub Actions 每天自动采集热点、AI 改写后，用这个 Token 写入 GitHub Gist。

**获取步骤**：
1. 打开 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选权限：`gist`（必须勾选）
4. 生成后复制这串字符（如 `ghp_xxxxxxxxxxxx`）

**注意**：Token 只在生成时显示一次，请妥善保存。如果泄露，可以立即删除重新生成。

### 2. 赛道关键词

**用途**：AI 改写热点时会根据你的赛道生成选题，避免内容太泛。

**示例**：
- `柯基狗狗、穿搭、化妆、护肤`（当前已配置）
- `短视频运营、自媒体起号`
- `AI工具效率、职场成长`
- `健身减脂、健康饮食`

建议给 1-3 个关键词，越具体越好。

### 3. 公众号来源

**用途**：速算练习、申论积累模块需要自动从微信文章/专辑导入内容。

**提供方式**：1-3 个微信公众号公开文章链接或专辑链接，逗号分隔。

**示例**：
```
https://mp.weixin.qq.com/s/xxxxxxxxxx,https://mp.weixin.qq.com/s/yyyyyyyyyy
```

**专辑链接格式**（推荐）：
```
https://mp.weixin.qq.com/mp/appmsgalbum?__biz=xxxxx&action=getalbum&album_id=yyyyy
```

如果你只有公众号名称，可以告诉我，我帮你找到对应的专辑链接。

---

## 三、部署步骤（需要你的 GitHub 账号）

### 步骤 1：创建 GitHub 仓库

1. 打开 https://github.com/new
2. 仓库名称填写：`creator-workbench`
3. 设置为 **Public**（必须公开，否则 GitHub Actions 定时任务不免费）
4. 点击 "Create repository"

### 步骤 2：上传项目文件

在仓库页面点击 "Upload files"，上传以下文件：

```
index.html
scripts/
  update_content.py
  initial_data.json
.github/
  workflows/
    update-gist.yml
```

**注意**：保持文件结构一致，不要改文件名。

### 步骤 3：启用 GitHub Pages

1. 在仓库页面点击 "Settings"
2. 左侧菜单选择 "Pages"
3. Source 选择 "Deploy from a branch"
4. Branch 选择 "main"，文件夹选择 "/ (root)"
5. 点击 "Save"

等待 1-2 分钟后，你会得到一个网址：
```
https://meng1777.github.io/creator-workbench/
```

手机浏览器打开这个网址即可使用。

---

## 四、配置 GitHub Secrets

在仓库页面点击 "Settings" → "Secrets and variables" → "Actions" → "New repository secret"，依次添加以下 Secrets：

| Secret 名称 | 内容 | 是否必填 |
|------------|------|----------|
| `GIST_ID` | 你创建的 Gist ID（见步骤五） | 是 |
| `GIST_TOKEN` | 你的 GitHub Token（ gist 权限） | 是 |
| `AI_API_KEY` | DeepSeek / OpenAI 等 API 密钥 | 是 |
| `AI_API_BASE` | API 基础地址，如 `https://api.deepseek.com/v1` | 否 |
| `AI_MODEL` | 模型名称，如 `deepseek-chat` | 否 |
| `NICHE_KEYWORDS` | 你的赛道关键词 | 是 |
| `WECHAT_SOURCES` | 公众号文章/专辑链接，逗号分隔 | 否 |

---

## 五、创建 GitHub Gist（数据存储）

1. 打开 https://gist.github.com
2. 创建一个新的 Gist
3. 文件名填写：`data.json`
4. 内容：复制 `scripts/initial_data.json` 的全部内容粘贴进去
5. Description 可选填："创作工作台云端数据"
6. 点击 "Create public gist"
7. 创建后，浏览器地址栏会变成类似：
   ```
   https://gist.github.com/你的用户名/abc123def456
   ```
   其中 `abc123def456` 就是 Gist ID，把它复制下来填入 GitHub Secret `GIST_ID`。

---

## 六、配置前端读取 Gist

手机打开网页后，点击"设置"（如果页面还没加设置入口，可以手动在浏览器控制台执行）：

```javascript
localStorage.setItem('cw_gist_username', '你的GitHub用户名');
localStorage.setItem('cw_gist_id', '你的GistID');
location.reload();
```

更好的方式：我可以在 `index.html` 里预留一个设置入口，你填写用户名和 Gist ID 后保存即可。

**Gist Raw URL 格式**：
```
https://gist.githubusercontent.com/你的用户名/你的GistID/raw/data.json
```

---

## 七、测试自动化

1. 配置完 Secrets 后，进入仓库 "Actions" 页面
2. 点击左侧 "每日热点采集与AI改写"
3. 点击右侧 "Run workflow" 手动触发一次
4. 等待几分钟后查看运行结果（绿色✓表示成功）
5. 成功后打开你的 Gist，查看 `data.json` 是否已更新
6. 手机上刷新网页，点击"选题灵感"或"爆款二创"的刷新按钮，看数据是否同步

---

## 八、常见问题

### Q1：为什么 GitHub 仓库必须公开？
A：GitHub 免费账户的私有仓库不支持定时触发 Actions（schedule），只有公开仓库才免费支持。

### Q2：GitHub Pages 国内访问慢吗？
A：GitHub Pages 在国内访问有时需要 3-5 秒加载。如果追求速度，可以额外部署到 Vercel / Netlify / Cloudflare Pages，这些也是免费的。

### Q3：AI API 用哪个？
A：推荐 DeepSeek（deepseek.com），价格低、中文好。也可以用 OpenAI / Claude / 其他兼容 OpenAI 格式的 API。

### Q4：微信公众号文章链接失效怎么办？
A：微信文章有时会过期。建议提供专辑链接（多个文章的集合），脚本会随机选择文章。如果专辑也失效，需要更新 WECHAT_SOURCES。

### Q5：手机上如何使用？
A：
- 直接手机浏览器打开 GitHub Pages 网址
- 可以添加到手机桌面（像 App 一样打开）
- iPhone：Safari 打开 → 分享 → 添加到主屏幕
- Android：Chrome 打开 → 菜单 → 添加到主屏幕

### Q6：数据会丢失吗？
A：
- 本地数据（计划、复盘、备忘录）存浏览器 localStorage，清除浏览器数据会丢失
- 云端数据（选题灵感、二创角度）存 GitHub Gist，不会丢失
- 建议定期导出本地数据备份

---

## 九、需要我帮你做什么

目前项目代码已经搭建完成，包含：
- ✅ 前端单文件 HTML（7个模块、抽屉导航、橄榄绿风格）
- ✅ GitHub Actions 工作流
- ✅ Python 采集 + AI 改写脚本
- ✅ 初始 Gist 数据
- ✅ 本部署指南

**你接下来需要做的**：
1. 提供 GitHub Token
2. 提供赛道关键词
3. 提供公众号来源（可选，先不配也能用）
4. 告诉我你的 GitHub 用户名，我帮你检查 Gist URL 是否正确

如果你愿意，我还可以帮你：
- 在 `index.html` 里添加一个可视化的设置入口（填写 Gist 用户名和 ID）
- 添加本地数据导出/导入功能
- 接入更多热榜平台

