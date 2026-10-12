# 持续增加模板

仓库按业务线组织，不把单一品牌或模版A写死在整个工程里。当前业务线为 `orthodontics`（正畸）与 `whitening`（美白）。新增其他业务线可在 `catalog.json` 中登记。

## 最小结构

```text
templates/<业务线>/<模板编号>/
  README.md             输入、输出、画面与语音规则
  make.py               可由统一入口调用的 Python 程序
  render.cjs            如模板使用 Node 渲染
  story.template.json   固定文案和场景
  assets/manifest.json  素材来源、哈希、使用范围
  assets/               此模板的已确认素材
  examples/             不含真实客户资料的测试输入
```

1. 给模板一个稳定、唯一的 `id`，不要重复使用 `ds-a`。名称、业务线、版本、相对路径、入口与 `outputPattern` 登记到根 `catalog.json`。
2. 从 `shared/runtime.py` 复用依赖定位与字体配置；路径全部相对本仓库，不能引用维护者桌面、个人 Skill、凭证或其他私有工程。
3. 统一入口：`video.py --template <id>`，后续参数传给模板入口。维持 `--name`、`--logo`、`--preview`、`--out`、`--resume` 约定；使用在线语音时明确授权参数和发送范围。
4. 文案、声音和素材保持业务线独立。美白模板必须登记自己的真实品牌资产、已确认表述和声音策略；不要自动沿用正畸的医疗内容。
5. **所有输出模式均以 `{clinic_name}.mp4` 结尾**，例如 `品牌-视频用途-{clinic_name}.mp4`。版本、日期和样片状态放目录/记录，不能加到门诊名称之后。
6. 交付 MP4、母版、字幕、音频、输入与 QA 分目录；默认不进入版本控制。保留准确的技术、画面与听感状态。
7. 为新增模板补充代表性输入：纯图形Logo、含名称Logo、长名称或特殊读音。先预览，查看关键帧，再做有旁白样片；不能只检查脚本运行成功。
8. 更新根 README 的已收录表、模板自己的说明、素材登记与 CHANGELOG，再发布新版本。只发布实际可执行模板，规划不能写成完成。

`docs/VOICE.md` 与 `docs/QA.md` 是公共流程；每个模板可补充专属规则。完整 yy-video Skill 不属于运行依赖，也不需要同事另装。
