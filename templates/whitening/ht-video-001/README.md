# HT视频001

皓得适门诊合作视频模板，版本 **1.1.0**。提供门诊名称与真实 Logo，在自己的电脑上生成 **门诊 × HiTeeth皓得适** 合作视频。

## 给 Codex 的制作请求

> 用 HT视频001 制作门诊合作视频。门诊名称：××口腔，Logo 见附件。先看原图判断是否已经包含门诊名称。首次使用在本项目内完成必要配置；允许将本次门诊名称和两段公开宣传文案发送至微软语音服务生成旁白。保留原件，检查产品图、字幕与声音，输出 HiTeeth皓得适-合作视频-××口腔.mp4。

本模板无需另装私有 Skill。共享依赖与安装方法见[仓库首页](../../../README.md)。

## 画面与内容

- 九场景：开场、门诊合作、评估、产品与感受、牙色记录、美白维护、服务价值、微笑场景、片尾。
- 1920 × 1080、16:9、30 fps、H.264/AAC；参考时长约89秒，门诊名称及旁白长度会改变对应场景时长。
- HP17 / HP30 使用新版原始实拍图（1677 × 1279 / 4450 × 3167），完整等比显示，不推拉、不平移；按旁白节点直接切换，不叠化。
- 保留“美白维护”，把门诊服务对应到消费者的“选择更清楚、过程有照顾、之后有指导”。
- 合作画面及片尾的“×”固定在画面横向中轴960px。真实门诊 Logo 不裁切、不拉伸，已含名称时不重复补字。
- 已裁除旧包装的动态镜头与原文字动画保持一致。人物素材是品牌情景示意，不代表使用者门诊实拍；医生评估、效果与感受因人而异的提示不可删除。

## 使用

在仓库根目录运行，Windows 使用 `.venv\Scripts\python.exe`：

```sh
# 九场景预览及两张产品关键帧：离线，不配音、不生成MP4
.venv/bin/python video.py --template ht-video-001 --name '示例口腔' --logo templates/whitening/ht-video-001/examples/demo-logo.svg --preview

# 正式制作流程；已有在线配音授权，Logo 已含名称
.venv/bin/python video.py --template ht-video-001 --name '示例口腔' --logo inputs/logo.png --logo-has-name --allow-online-tts

# 在线服务不可用时，导入获准的两段完整旁白
.venv/bin/python video.py --template ht-video-001 --name '示例口腔' --logo inputs/logo.png --voice-dir inputs/voice
```

`--out output/任务目录` 指定独立目录；相同输入、模板指纹和模式才可 `--resume`。`--offline` 禁止请求在线配音；缺少有效缓存时停止。`--name-color '#263F94'` 调整补充门诊名称颜色。Logo 是否含名称由看图后决定，纯图形不加 `--logo-has-name`。

成片为 `renders/HiTeeth皓得适-合作视频-门诊名称.mp4`，文件名以门诊名称结尾。`renders/` 仅放MP4，字幕在 `source/`，封面、关键帧和检查在 `qa/`，播放页在任务根目录；准确路径与审片状态见 `delivery.json`。版本与日期保留在目录中。

## 旁白策略

| 项目 | HT视频001 |
|---|---|
| 声音 | 微软晓晓 `zh-CN-XiaoxiaoNeural` |
| 语速 / 音高 | `+18%` / `-1Hz` |
| 通用缓存 | opening、assessment、comfort、record、maintenance、service、benefits，七段，不含门诊名称 |
| 新门诊重配 | partnership、closing，两段整句旁白 |
| 同步 | 在线配音用词边界重新计算字幕、场景时长及强调节点 |
| 混音 | `loudnorm=I=-18:TP=-1.5:LRA=7`；48kHz、单声道；无BGM |

在线请求只发送公开旁白文字及门诊名称，不上传 Logo、产品图或患者资料。`--allow-online-tts` 表示本次用途已获使用者授权。在线服务可用性取决于网络及上游，本次开源发布没有重新验证在线配音，不承诺始终可用。

`--voice-dir` 需要 `partnership.mp3` 和 `closing.mp3`，也支持同名 WAV/M4A，每段只能有一份。必须对应 `template.json` 中本次门诊的**完整场景文案**，不得把门诊名称拼接进旧声音。本地音频缺少词边界，程序按字数估算字幕和强调时间，并记录 `estimated-from-whole-scene-audio`；需逐句复核同步、名称读音、音色与节奏，不能把估算时间当作精确语音对齐。

## 验收与素材

新任务默认「有旁白样片」。检查完整解码、帧数、音轨、字幕完整性后，查看准确MP4中的 Logo、产品段、合作画面与片尾，并完成真实连续看听；技术检查不代替人工听审。使用者的输入与结果均保留在本地，不提交GitHub。

代码及文档按仓库MIT许可证；品牌、产品图、人物素材、声音与字体分别遵循 [ASSETS.md](../../../ASSETS.md)，不自动套用MIT。逐文件来源与哈希见 `assets/manifest.json`。示例Logo为技术测试标识，不代表真实门诊合作。
