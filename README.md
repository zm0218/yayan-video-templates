# 牙颜视频模版库

**下载项目，在 Codex 中打开，提供门诊名称和 Logo，在自己的电脑上完成视频制作。**

这是持续增加模板的本地制作库，按 **正畸、美白** 等业务线组织。当前首批收录 **正畸 · DS模版A**；美白目录已预留，尚未收录可执行模板。所有制作在使用者电脑上完成，GitHub 用于分发和版本更新。

## 给同事：从这里开始

1. 点击 GitHub 的 **Code → Download ZIP** 并解压，或克隆此仓库。
2. 在 Codex 中打开解压后的项目文件夹（包含本 README 和 `AGENTS.md` 的目录）。
3. 提供门诊 Logo，然后发送下面这段话：

> 请按本仓库的 DS模版A 制作视频。门诊名称：××口腔，Logo 见附件。首次使用请先检查环境，并在本项目内完成必要配置；允许将本次门诊名称及三段公开宣传文案发送至微软语音服务生成旁白。保留原稿和母版，检查 Logo、字幕与读音。输出文件名为 DeepSmile-合作视频-××口腔.mp4。

只提供 Logo 时，Codex 先看图读取名称；无法辨认、名称有冲突或有不确定读音时才补充确认。**不需要另外安装 yy-video Skill**，本仓库已经包含制作、声音和验收规则。

首次安装依赖需要联网，门诊专属配音也需要联网；Logo 和画面渲染留在本机。生成的视频默认是**有旁白样片**，完整观看、听审并确认后再对外使用。

**当前配音可用性说明（2026-10-12）：** 本次联网验证收到微软语音服务 HTTP 403，原制作环境也出现相同拒绝；尚未确认在线语音恢复。可先离线预览，或按 [声音说明](docs/VOICE.md) 导入获准的三段完整旁白。不能把本次发布描述为已验证「任意电脑一句话自动配音成功」。

## 已收录模板

| 业务线 | 模板 | 编号 | 输入 | 输出 |
|---|---|---|---|---|
| 正畸 | [DS模版A](templates/orthodontics/ds-a/README.md) | `ds-a` | 门诊名称、Logo | 8场景、约64秒、1920×1080、30fps、中文女声、单层字幕 |
| 美白 | 待增加 | — | — | — |

模板索引见 [catalog.json](catalog.json)。新增正畸、美白或其他模板见 [扩展说明](docs/ADDING_TEMPLATES.md)。

## 首次配置

需要 **Python 3.10+（建议3.12）**、**Node.js 20.9+（建议22或更新的LTS，含npm）**。从 [Python](https://www.python.org/downloads/) 和 [Node.js](https://nodejs.org/en/download) 官方渠道安装；Codex 可先检查本机已有环境，不重复安装。

在项目根目录执行一次：

```sh
# macOS / Linux
python3 bootstrap.py
```

```powershell
# Windows
py -3 bootstrap.py
```

脚本只在项目内创建 `.venv/` 和 `node_modules/`，安装固定版本依赖并检查环境，不修改其他项目或全局 Python 包。FFmpeg / FFprobe 随项目 npm 依赖按平台获取，不需要同事手动寻找路径。首次配置不会发起配音请求。

## 制作与预览

通常直接在 Codex 中提出制作要求即可。下面的命令供排错和人工运行使用。

```sh
# macOS / Linux：列出模板
.venv/bin/python video.py --list

# 离线检查八场景画面，不配音、不生成 MP4
.venv/bin/python video.py --template ds-a --name '示例口腔' --logo 'templates/orthodontics/ds-a/examples/demo-logo.svg' --preview

# 完整制作；Logo 已包含门诊名称时，加 --logo-has-name
.venv/bin/python video.py --template ds-a --name '示例口腔' --logo 'inputs/logo.png' --allow-online-tts
```

Windows 将 `.venv/bin/python` 换为 `.venv\Scripts\python.exe`，参数一致。将文件路径放进引号；可使用中文目录及空格。`examples/demo-logo.svg` 仅是测试标识，不可当作真实门诊 Logo。

配音使用微软在线语音服务，仅发送门诊名称与三段文案，不上传 Logo。`--allow-online-tts` 记录本次调用已获授权；**下载本仓库不等于自动同意向任何外部服务发送资料**。首次使用的话术已说明并授权这一用途，之后同用途制作按使用者已有授权执行。语音规则见 [VOICE.md](docs/VOICE.md)。

## 成片在哪里？怎么命名？

默认保存到 `output/ds-a/job-门诊名称-时间/`：

```text
renders/       只放对外交付 MP4
input/         门诊 Logo 原件
intermediate/  静音画面母版
audio/         原始与处理后的旁白
source/        模板快照、素材副本、字幕源
qa/            关键帧、联系表、媒体及音频检查
delivery.json  成片路径与待验收状态
```

**所有模板的成片文件名必须以门诊名称结尾，扩展名为 `.mp4`。**

- DS模版A：`DeepSmile-合作视频-门诊名称.mp4`
- 后续模板：`品牌或主题-视频用途-门诊名称.mp4`
- 名称后不追加日期、版本号、横竖版或“样片”。版本放文件夹，状态放制作记录。
- 不能用于 Windows 文件名的字符会明确报错，不能悄悄修改门诊正式名称。

门诊 Logo、成片、临时声音及本机配置默认被 `.gitignore` 排除；请勿强制提交真实客户输入和制作目录。

## 检查与更新

- [通用验收清单](docs/QA.md)：技术检查、实图查看与完整看听分别记录。
- [声音流程与规范](docs/VOICE.md)：保留既有女声、读音修正和整句配音方法。
- [故障处理](docs/TROUBLESHOOTING.md)：环境、网络、恢复制作、字幕及声音。
- [平台验证记录](docs/VALIDATION.md)：以实际记录为准，不能把代码兼容或 CI 通过当作同事端验收。
- Git 克隆用户可在无本地源码改动时 `git pull --ff-only`；ZIP 用户下载新版到新文件夹，保留原文件夹中的 `inputs/` 和 `output/`。每次改依赖后重新运行 `bootstrap.py`。

## 开源与素材说明

原创程序代码及文档采用 [MIT](LICENSE)。图片、品牌标识、语音和字体按 [ASSETS.md](ASSETS.md) 单独说明，不因为代码开源就变成公共领域素材。品牌合作宣传必须符合真实合作关系；AI 人物及产品界面仅作情景与沟通示意，不代表真实患者或治疗效果。
