## Dify 插件开发指南

你好，看起来你已经创建了一个插件，现在让我们开始开发吧！

### 选择你想要开发的插件类型

在开始之前，你需要一些关于插件类型的入门知识，插件支持在 Dify 中扩展以下能力：
- **工具**：工具提供者，如 Google 搜索、Stable Diffusion 等。它可以用于执行特定任务。
- **模型**：模型提供者，如 OpenAI、Anthropic 等。你可以使用它们的模型来增强 AI 能力。
- **端点**：类似于 Dify 中的服务 API 或 Kubernetes 中的 Ingress，你可以将一个 HTTP 服务扩展为端点，并使用自己的代码控制其逻辑。

根据你想要扩展的能力，我们将插件分为三种类型：**工具**、**模型**和**扩展**。

- **工具**：它是一个工具提供者，但不仅限于工具，你可以在其中实现一个端点，例如，如果你正在构建一个 Discord Bot，你需要同时实现 `发送消息` 和 `接收消息`，**工具**和**端点**都是必需的。
- **模型**：只是一个模型提供者，不允许扩展其他功能。
- **扩展**：其他时候，你可能只需要一个简单的 HTTP 服务来扩展功能，**扩展**是适合你的选择。

我相信你在创建插件时已经选择了正确的类型，如果没有，你可以在稍后通过修改 `manifest.yaml` 文件来更改它。

### 清单

现在你可以编辑 `manifest.yaml` 文件来描述你的插件，以下是它的基本结构：

- version（版本，必填）：插件的版本
- type（类型，必填）：插件的类型，目前仅支持 `plugin`，未来支持 `bundle`
- author（字符串，必填）：作者，它是市场中的组织名称，也应等于仓库所有者的名称
- label（标签，必填）：多语言名称
- created_at（RFC3339，必填）：创建时间，市场要求创建时间必须早于当前时间
- icon（资产，必填）：图标路径
- resource（对象）：要应用的资源
  - memory（int64）：最大内存使用量，主要与无服务器 SaaS 上的资源申请相关，单位字节
  - permission（对象）：权限申请
    - tool（对象）：反向调用工具权限
      - enabled（布尔值）
    - model（对象）：反向调用模型权限
      - enabled（布尔值）
      - llm（布尔值）
      - text_embedding（布尔值）
      - rerank（布尔值）
      - tts（布尔值）
      - speech2text（布尔值）
      - moderation（布尔值）
    - node（对象）：反向调用节点权限
      - enabled（布尔值）
    - endpoint（对象）：允许注册端点权限
      - enabled（布尔值）
    - app（对象）：反向调用应用权限
      - enabled（布尔值）
    - storage（对象）：申请持久存储权限
      - enabled（布尔值）
      - size（int64）：最大允许的持久内存，单位字节
- plugins（对象，必填）：插件扩展特定能力的 YAML 文件列表，插件包中的绝对路径，如果你需要扩展模型，你需要定义一个类似于 openai.yaml 的文件，并在这里填写路径，路径上的文件必须存在，否则打包会失败。
  - 格式
    - tools（列表[字符串]）：扩展的工具供应商，有关详细格式，请参考 [工具指南](https://docs.dify.ai/plugins/schema-definition/tool)
    - models（列表[字符串]）：扩展的模型供应商，有关详细格式，请参考 [模型指南](https://docs.dify.ai/plugins/schema-definition/model)
    - endpoints（列表[字符串]）：扩展的端点供应商，有关详细格式，请参考 [端点指南](https://docs.dify.ai/plugins/schema-definition/endpoint)
  - 限制
    - 不允许同时扩展工具和模型
    - 不允许没有任何扩展
    - 不允许同时扩展模型和端点
    - 目前每种类型的扩展最多只支持一个供应商
- meta（对象）
  - version（版本，必填）：清单格式版本，初始版本 0.0.1
  - arch（列表[字符串]，必填）：支持的架构，目前仅支持 amd64 arm64
  - runner（对象，必填）：运行时配置
    - language（字符串）：目前仅支持 python
    - version（字符串）：语言版本，目前仅支持 3.12
    - entrypoint（字符串）：程序入口，在 python 中应该是 main

### 安装依赖

- 首先，你需要一个 Python 3.11+ 环境，因为我们的 SDK 需要它。
- 然后，安装依赖：
    ```bash
    pip install -r requirements.txt
    ```
- 如果你想添加更多依赖，可以将它们添加到 `requirements.txt` 文件中，一旦你在 `manifest.yaml` 文件中设置了运行时为 python，`requirements.txt` 将会自动生成并用于打包和部署。

### 实现插件

现在你可以开始实现你的插件，通过以下示例，你可以快速理解如何实现自己的插件：

- [OpenAI](https://github.com/langgenius/dify-plugin-sdks/tree/main/python/examples/openai): 最佳实践的模型提供者
- [Google Search](https://github.com/langgenius/dify-plugin-sdks/tree/main/python/examples/google): 一个简单的工具提供者示例
- [Neko](https://github.com/langgenius/dify-plugin-sdks/tree/main/python/examples/neko): 一个有趣的端点组示例

### 测试和调试插件

你可能已经注意到在插件根目录下有一个 `.env.example` 文件，只需将其复制为 `.env` 并填写相应的值，如果你想要本地调试插件，需要设置一些环境变量。

- `INSTALL_METHOD`: 设置为 `remote`，你的插件将通过网络连接到 Dify 实例。
- `REMOTE_INSTALL_URL`: 你的 Dify 实例的插件守护进程服务的调试主机和端口 URL，例如 `debug.dify.ai:5003`。可以使用 [Dify SaaS](https://debug.dify.ai) 或 [自托管 Dify 实例](https://docs.dify.ai/en/getting-started/install-self-hosted/readme)。
- `REMOTE_INSTALL_KEY`: 你应该从你使用的 Dify 实例获取调试密钥，在插件管理页面的右上角，你会看到一个带有 `debug` 图标的按钮，点击它即可获取密钥。

运行以下命令以启动你的插件：

```bash
python -m main
```

刷新你的 Dify 实例页面，你应该能够在列表中看到你的插件，但它会被标记为 `debugging`，你可以正常使用它，但不建议用于生产。

### 发布和更新插件

为了简化插件更新流程，你可以配置 GitHub Actions 以在每次创建发布时自动创建 PR 到 Dify 插件仓库。

##### 前提条件

- 你的插件源代码仓库
- Dify-plugins 仓库的 fork
- 你的 fork 中正确的插件目录结构

#### 配置 GitHub Action

1. 创建一个具有对你 forked 仓库写权限的个人访问令牌
2. 将其作为名为 `PLUGIN_ACTION` 的秘密添加到你的源代码仓库设置中
3. 在 `.github/workflows/plugin-publish.yml` 创建一个工作流文件

#### 使用

1. 更新你的代码和 `manifest.yaml` 中的版本
2. 在你的源代码仓库中创建一个发布
3. 该操作会自动打包你的插件并创建一个 PR 到你的 forked 仓库

#### 优点

- 消除了手动打包和 PR 创建步骤
- 确保了你的发布流程的一致性
- 节省了频繁更新时的时间

---

有关详细设置说明和示例配置，请访问：[GitHub Actions Workflow Documentation](https://docs.dify.ai/plugins/publish-plugins/plugin-auto-publish-pr)

### 打包插件

最后，只需通过运行以下命令来打包你的插件：

```bash
dify-plugin plugin package ./ROOT_DIRECTORY_OF_YOUR_PLUGIN
```

你将得到一个 `plugin.difypkg` 文件，这就完成了，你现在可以将其提交到市场，期待你的插件被列出！

## 用户隐私政策

请填写插件的隐私政策，如果你希望将其发布到市场，请参考 [PRIVACY.md](PRIVACY.md) 以获取更多详细信息。