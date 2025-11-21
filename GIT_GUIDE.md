# Git 使用指南

## 仓库信息

- **仓库路径**: `/home/lyl610/green1112/appworld_green_agent`
- **分支**: `master`
- **初始提交**: 089b66c
- **文件数**: 48 个文件
- **代码行数**: 8,261 行

## 基本 Git 命令

### 查看状态

```bash
# 查看当前状态
git status

# 查看提交历史
git log --oneline

# 查看详细提交历史
git log --graph --decorate --all

# 查看最近 5 次提交
git log -5
```

### 添加和提交更改

```bash
# 查看修改的文件
git status

# 添加特定文件
git add <file>

# 添加所有修改
git add .

# 提交更改
git commit -m "描述你的更改"

# 添加并提交（一步完成）
git commit -am "描述你的更改"
```

### 查看差异

```bash
# 查看未暂存的更改
git diff

# 查看已暂存的更改
git diff --staged

# 查看特定文件的更改
git diff <file>
```

### 撤销更改

```bash
# 撤销工作目录中的更改（危险！）
git checkout -- <file>

# 取消暂存文件
git reset HEAD <file>

# 修改最后一次提交
git commit --amend

# 回退到上一次提交（保留更改）
git reset --soft HEAD^

# 回退到上一次提交（丢弃更改，危险！）
git reset --hard HEAD^
```

## 分支管理

### 创建和切换分支

```bash
# 查看所有分支
git branch

# 创建新分支
git branch <branch-name>

# 切换分支
git checkout <branch-name>

# 创建并切换分支（一步完成）
git checkout -b <branch-name>

# 删除分支
git branch -d <branch-name>
```

### 合并分支

```bash
# 合并指定分支到当前分支
git merge <branch-name>

# 取消合并
git merge --abort
```

## 远程仓库

### 添加远程仓库

```bash
# 添加远程仓库
git remote add origin <repository-url>

# 查看远程仓库
git remote -v

# 重命名远程仓库
git remote rename origin new-origin

# 删除远程仓库
git remote remove origin
```

### 推送和拉取

```bash
# 推送到远程仓库
git push origin master

# 首次推送并设置上游
git push -u origin master

# 拉取远程更改
git pull origin master

# 仅获取远程更改（不合并）
git fetch origin
```

## 项目特定的工作流

### 功能开发工作流

```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 进行开发和提交
git add .
git commit -m "实现新功能"

# 3. 切换回主分支
git checkout master

# 4. 合并功能分支
git merge feature/new-feature

# 5. 删除功能分支
git branch -d feature/new-feature
```

### 修复 Bug 工作流

```bash
# 1. 创建修复分支
git checkout -b fix/bug-description

# 2. 修复 bug 并提交
git add .
git commit -m "修复: bug 描述"

# 3. 切换回主分支并合并
git checkout master
git merge fix/bug-description

# 4. 删除修复分支
git branch -d fix/bug-description
```

### 版本发布工作流

```bash
# 1. 创建版本标签
git tag -a v1.0.0 -m "Version 1.0.0"

# 2. 推送标签到远程
git push origin v1.0.0

# 3. 查看所有标签
git tag

# 4. 查看标签详情
git show v1.0.0
```

## 提交信息规范

建议使用以下格式编写提交信息：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更改
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（既不是新功能也不是 Bug 修复）
- `perf`: 性能优化
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具的变动

### 示例：

```bash
git commit -m "feat(white-agent): 添加 MCP 支持

- 实现 MCP 客户端连接
- 添加工具发现和调用功能
- 更新文档

Closes #123"
```

## .gitignore 文件

已配置忽略以下内容：
- Python 缓存文件 (`__pycache__`, `*.pyc`)
- 虚拟环境 (`venv/`, `env/`)
- IDE 配置 (`.vscode/`, `.idea/`)
- AppWorld 数据文件 (`data/`, `*.db`)
- 日志文件 (`*.log`, `logs/`)
- 临时文件 (`*.tmp`, `tmp/`)

## 有用的 Git 别名

可以在 `~/.gitconfig` 中添加以下别名：

```ini
[alias]
    st = status
    co = checkout
    br = branch
    ci = commit
    unstage = reset HEAD --
    last = log -1 HEAD
    visual = log --graph --decorate --oneline --all
    amend = commit --amend --no-edit
```

使用别名：
```bash
git st           # 等同于 git status
git co master    # 等同于 git checkout master
git visual       # 可视化提交历史
```

## 常见场景

### 场景 1: 撤销最后一次提交但保留更改

```bash
git reset --soft HEAD^
```

### 场景 2: 暂存当前工作以切换分支

```bash
# 暂存当前工作
git stash

# 切换分支并工作
git checkout other-branch

# 回到原分支并恢复工作
git checkout original-branch
git stash pop
```

### 场景 3: 查看某个文件的历史

```bash
# 查看文件的提交历史
git log -- path/to/file

# 查看文件的更改历史
git log -p -- path/to/file
```

### 场景 4: 恢复已删除的文件

```bash
# 查找删除文件的提交
git rev-list -n 1 HEAD -- <file_path>

# 从该提交恢复文件
git checkout <commit>^ -- <file_path>
```

## 注意事项

1. **不要修改已推送的提交历史**（除非你知道自己在做什么）
2. **频繁提交**：小而频繁的提交比大而稀少的提交更好
3. **编写清晰的提交信息**：未来的你会感谢现在的你
4. **推送前先拉取**：避免冲突
5. **使用分支**：保持 master 分支稳定

## 下一步

1. **设置远程仓库**（如果需要）：
   ```bash
   # GitHub
   git remote add origin https://github.com/username/appworld_green_agent.git
   git push -u origin master
   
   # GitLab
   git remote add origin https://gitlab.com/username/appworld_green_agent.git
   git push -u origin master
   ```

2. **创建 .gitattributes**（可选）：
   ```bash
   echo "*.py text eol=lf" > .gitattributes
   git add .gitattributes
   git commit -m "chore: 添加 .gitattributes"
   ```

3. **设置 Git 配置**（如果还没有）：
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   git config --global core.editor "vim"  # 或你喜欢的编辑器
   ```

## 资源

- [Git 官方文档](https://git-scm.com/doc)
- [Pro Git 书籍](https://git-scm.com/book/zh/v2)
- [GitHub Git 指南](https://guides.github.com/)
- [Git 可视化学习](https://learngitbranching.js.org/)

## 当前仓库结构

```
appworld_green_agent/
├── .git/                    # Git 仓库数据
├── .gitignore              # Git 忽略文件配置
├── README.md               # 项目说明
├── main.py                 # CLI 入口
├── requirements.txt        # Python 依赖
├── src/                    # 源代码
│   ├── green_agent/       # Green Agent 实现
│   ├── white_agent/       # White Agent 实现
│   ├── evaluator/         # 评估器
│   └── util/              # 工具函数
├── startup.sh             # Cloud Run 启动脚本
├── run.sh                 # AgentBeats 控制器脚本
└── [文档文件...]         # 各种文档
```

---

**提示**: 使用 `git help <command>` 获取任何命令的详细帮助。

