# Bug 修复报告

## 修复时间
2026-03-06

## 修复的 Bug 列表

### Bug 1: 狼人 AI 返回无效目标 ✅ 已修复

**问题描述**:
狼人行动时，AI 经常返回无效目标（已死亡玩家或狼人队友），导致出现 "AI 返回了无效目标，已重新选择" 的提示。

**修复方案**:
- 在 `ai/agent.py` 的 `decide_night_action()` 方法中，增强了 prompt 提示
- 明确要求 AI 返回的 target 必须是存活玩家列表中的数字
- 添加注意事项：不能选择狼人队友

**修改文件**:
- `ai/agent.py` - 狼人行动 prompt

---

### Bug 2: 预言家重复查验同一玩家 ✅ 已修复

**问题描述**:
游戏日志显示预言家查验记录为 `[3, 8, 8, 9]`，玩家 8 被查验了 2 次。

**修复方案**:
1. 在 `core/state.py` 中添加 `seer_checked_players` 字段，记录已查验的玩家
2. 在 `core/game_engine.py` 的 `_handle_seer_action()` 方法中：
   - 传递已查验玩家列表给 AI
   - 如果 AI 返回已查验的玩家，自动重新选择
3. 在 `ai/agent.py` 的 `decide_night_action()` 方法中：
   - 预言家 prompt 明确告知已查验的玩家列表
   - 要求 AI 不能查验已经查验过的玩家

**修改文件**:
- `core/state.py` - 添加 `seer_checked_players` 字段
- `core/game_engine.py` - `_handle_seer_action()` 方法
- `ai/agent.py` - `decide_night_action()` 方法

---

### Bug 3: 警长竞选无人投票 ✅ 已修复

**问题描述**:
第一天警长竞选时出现 `无人投票，无人当选警长` 的情况。

**修复方案**:
1. 提高 AI 参选概率从 50% 到 70%
2. 如果无人自愿参选，强制随机选择 2-3 名 AI 参选
3. AI 投票时如果弃权，自动随机投票给一个候选人

**修改文件**:
- `core/game_engine.py` - `_run_president_election()` 方法

---

### Bug 4: 死人出现在信任/怀疑列表中 ✅ 已修复

**问题描述**:
投票前辩论时，玩家仍然信任/怀疑已死亡的玩家。

**修复方案**:
- 在 `ai/agent.py` 的 `vote()` 方法中，过滤掉已死亡的玩家
- 只显示存活玩家的信任/怀疑列表

**修改文件**:
- `ai/agent.py` - `vote()` 方法

---

### Bug 5: 狼人遗言暴露身份 ✅ 已修复

**问题描述**:
```
[8 号玩家 (张仪)-狼人] [遗言] 我是 werewolf，希望大家能找到狼人。
```
狼人直接暴露了身份。

**修复方案**:
- 在 `ai/agent.py` 的 `make_last_words()` 方法中：
  - 为狼人添加特殊的遗言 prompt
  - 要求狼人绝对不能暴露身份，要假装是好人
  - 提供默认遗言防止暴露

**修改文件**:
- `ai/agent.py` - `make_last_words()` 方法

---

### Bug 6: 已死亡玩家仍然有内心独白记录 ✅ 已修复

**问题描述**:
在游戏日志中，多个已死亡玩家仍然有 `inner_thought` 事件记录。

**修复方案**:
- 在 `core/game_engine.py` 的 `_run_discussion()` 方法中：
  - 记录内心独白前检查玩家是否仍然存活
  - 只有存活玩家才记录内心独白

**修改文件**:
- `core/game_engine.py` - `_run_discussion()` 方法

---

## 修改文件汇总

| 文件 | 修改内容 |
|------|----------|
| `ai/agent.py` | 狼人行动 prompt、预言家查验 prompt、投票过滤死人、狼人遗言、死人发言检查 |
| `core/state.py` | 添加 `seer_checked_players` 字段 |
| `core/game_engine.py` | 预言家行动处理、警长竞选、讨论阶段死人检查 |

---

## 测试建议

运行完整游戏测试，验证以下场景：

1. **狼人行动**: 不再出现 "AI 返回了无效目标" 提示
2. **预言家查验**: 查验记录中不再有重复玩家
3. **警长竞选**: 确保有候选人和投票
4. **投票逻辑**: 信任/怀疑列表中没有死人
5. **狼人遗言**: 狼人不会暴露身份
6. **死人发言**: 日志中没有死人的内心独白

---

## 运行测试

```bash
# 运行完整游戏测试
python test_full_game.py

# 分析游戏日志
python analyze_game_log.py
```
