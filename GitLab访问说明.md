# GitLab 仓库访问与推送说明

## 仓库地址格式
- GitLab.com：`https://gitlab.com/<用户名或组织>/<项目名>`
- 自建 GitLab：`https://<你的GitLab域名>/<组或用户>/<项目名>`
- 代码远程地址（HTTPS）：`https://gitlab.com/<用户>/<项目>.git`
- 代码远程地址（SSH）：`git@gitlab.com:<用户>/<项目>.git`

> 说明：当前项目已推送到 GitHub（`https://github.com/chiweiw/jw3_bz`）。如需迁移或镜像到 GitLab，请先在 GitLab 创建项目，再按下述步骤推送。

## 浏览器访问
- 直接在浏览器输入你的仓库网页地址，例如：
  - GitLab.com：`https://gitlab.com/chiweiw/jw3_bz`（示例，需以你实际项目为准）
  - 自建 GitLab：`https://gitlab.<你的域名>/<组>/<项目>`

## 创建 GitLab 项目
1. 登录 GitLab，点击 “New project”。
2. 填写 `Project name`（如 `jw3_bz`）、选择可见性（Public/Private）。
3. 不勾选初始化内容（README/.gitignore/License），避免首推冲突。
4. 创建后获得仓库地址（HTTPS 或 SSH）。

## 设置远程并推送（从本地到 GitLab）
- HTTPS 方式（推荐有 PAT 时使用）：
  - `git remote add gitlab https://gitlab.com/<用户>/<项目>.git`
  - 或替换远程：`git remote set-url gitlab https://gitlab.com/<用户>/<项目>.git`
  - 首次推送：`git push -u gitlab main`
  - 认证提示时使用用户名 + Personal Access Token（PAT）作为“密码”。

- SSH 方式（推荐稳定性好）：
  - 本机生成/配置 SSH 公钥，并在 GitLab 账户的 `SSH Keys` 中添加公钥。
  - 设置远程：`git remote add gitlab git@gitlab.com:<用户>/<项目>.git`
  - 首次推送：`git push -u gitlab main`

> 你也可以保持 GitHub 为 `origin`，新增 GitLab 作为 `gitlab`，实现双远程：
> - 推送 GitHub：`git push -u origin main`
> - 推送 GitLab：`git push -u gitlab main`

## 常见问题与排查
- 404（页面不存在）：确认项目是否创建成功、URL 是否正确、大小写是否一致。
- 403（无权限）：检查项目访问权限、成员角色、是否登录正确账户。
- 401（认证失败）：HTTPS 场景使用 PAT；SSH 场景检查密钥是否添加并生效。
- 推送被拒绝（non-fast-forward）：`git pull gitlab main --rebase` 后再推送，或确保远程为空仓。
- 网络问题（端口/证书/代理）：改用 SSH 地址或在受信网络环境下重试。

## GitLab Pages（静态站点）
- GitLab Pages 通常通过 CI 将构建产物目录发布为 `public`。
- 若需发布 `docs/` 为站点，可在项目根添加 CI 配置（示例）：
  ```yaml
  pages:
    stage: deploy
    script:
      - mkdir -p public
      - cp -r docs/* public/
    artifacts:
      paths:
        - public
    only:
      - main
  ```
- 上述配置会将 `docs/` 的内容复制到 `public/`，由 Pages 提供访问（实际域名由 GitLab Pages 设置确定）。

## 当前项目建议
- 继续以 `docs/` 作为输出目录，用于 GitHub Pages；如需镜像到 GitLab Pages，可按上节添加 CI。
- 数据更新命令：
  - `uv run skill-growth-report --input 1.txt --site-dir docs --db-path skill_report.db --jump-threshold 2.0`
- SQLite 文件位置：项目根目录 `skill_report.db`（可用 `--db-path` 调整；已加入 `.gitignore`）。

