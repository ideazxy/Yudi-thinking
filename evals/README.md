# 行为回归

用同一题、同一份材料分别运行裸 agent、旧版与候选版。三组工作区使用相同输入，仅变更 Yudi Thinking 的安装情况。所有业务记录均为虚构样本。运行需要 Python 3.9+ 和 Git，实际模型运行使用自己的 agent。

[九个场景及逐题判据](cases.json) 包含此前 PR #2 的四类场景（弱证据、已确认规则交接、多边平台、前提推翻），以及纯翻译、已授权改稿、可自行读取的证据、内部多角色和只读评审。前提推翻题把前几轮决定作为记录提供，检验如何处理变更。

## 准备对照

在仓库根目录运行。下面用 2026-08-01 的主分支版本作为旧版，输出放在新的临时目录。

```bash
trial_root=$(mktemp -d)
git worktree add --detach "$trial_root/old" 52cae28c189e844b7e8b063cb956267de913a6ef
python3 evals/replay.py prepare --old "$trial_root/old" --out "$trial_root/runs"
```

只跑指定题时，在 prepare 命令末尾加上例如 `--case authorized-edit --case translation-only`。每次对照都用新的输出目录。题目在各组的 `prompt.txt`，原始材料和该组的可发现技能在 `work/`。评分标准留在仓库中，工作区不包含它们。

## 运行

固定模型、推理设置、工具和权限。用无其他同名或同类业务技能的配置，从各自的 `work/` 启动全新会话，原样提交题目。默认测自动触发，无须在提示里点名技能。下例使用支持仓库级 `.agents/skills` 的 Codex CLI。将 `model` 替换为自己有权使用的同一模型，先确认宿主允许加载这个临时工作区内的技能。

```bash
model=YOUR_MODEL
for trial in "$trial_root"/runs/*/*; do
  codex exec --ephemeral -m "$model" -s workspace-write -C "$trial/work" --json \
    -o "$trial/answer.md" - < "$trial/prompt.txt" > "$trial/trace.jsonl" || break
done
python3 evals/replay.py check-files --out "$trial_root/runs"
```

也可使用其他宿主：仅调整其仓库级技能发现方式，三组保持相同的工具与设置。保存首轮最终答复到对应的 `answer.md`，另存工具记录。手动点名技能的运行应单独记录。结果与工作区保留在临时目录，完成后可用 `git worktree remove "$trial_root/old"` 解除旧版检出。

## 判读

`check-files` 检查指定文件是否真的发生变更、是否多改或新增文件，并标记缺少答复的场次。它只检查路径。对改稿题还需看实际差异，其他题读答复与取证记录：

| 观察项 | 记录方式 |
|---|---|
| 触发 | 对照 `skill_expected`（默认应触发）。依据工具记录标为已加载、未加载或不可观察。裸 agent 记为不适用。 |
| 额外追问 | 统计首轮实际阻塞交付、且可从已有材料回答或已获授权的问题。标出正当的待决事项。 |
| 证据越级 | 逐项记下被当作事实、却缺少对应数据或行为的主张。 |
| 关键行为 | 对照每题 `checks` 给出通过、遗漏或证据不足，附一句原文、工具结果或文件差异。 |

优先盲读去掉版本标签的结果，再核对工具记录。模型输出有波动，单次差异只能作为线索。涉及删留规则的决定，用独立会话复跑发生分歧的题。
