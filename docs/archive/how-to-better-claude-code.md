# How to Better Use Claude Code

A practical guide synthesized from presentations by **Patrick Ellis** and **Anand Tyagi** (2025).

---

## What Claude Code Actually Is

Claude Code is **more than code generation** - it's the first truly competent AI agent we get to interface with directly.

**Key characteristics:**

- Claude fine-tuned/RL'd specifically for Claude Code tools
- Access to tools: bash, file operations, web search, todo lists, sub-agents, MCP servers
- Model switching via `/model` command (Sonnet 4 vs Opus 4)

### The Agent Loop

```
Get Task → Add to Task List → Do Task → Reflect on Output → Output
```

Each "Do Task" step involves **tool calls**: reading files, searching, executing commands, or MCP calls.

---

## Types of AI Agents (Context)

| Type                 | Examples                                          |
| -------------------- | ------------------------------------------------- |
| **Chat-based**       | ChatGPT, Gemini, Claude Desktop                   |
| **CLI/IDE Agent**    | Claude Code, Cursor, Windsurf, Kiro, Cline        |
| **Background Agent** | Codex, Jules, Claude Code + GitHub Actions, Devin |
| **Agent Swarm**      | Factory, custom multi-agent workflows             |

---

## What Agents Need for Great Performance

### 1. Context

The **most important factor**. Methods to provide context:

- **Planning Mode** - Use prompting to think through problems
- **`/context` directory** - Following Amazon Kiro's pattern: `requirements.md`, `design.md`, `task-list.md`
- **MCPs** - Playwright, GitHub, Context7 for live data
- **`/add-dir` command** - Add entire directories to context
- **Sub-agents** - Use to summarize and keep everything in context

### 2. Evals (Quality Controls)

- Examples of good/bad outputs
- Linters and standards
- Acceptance criteria
- Automated tests

### 3. Tools

- MCP servers (local and remote)
- Web search capabilities
- Bash/shell access

---

## CLAUDE.md Mastery

The **main context file** - it becomes part of every prompt Claude receives.

> "Your CLAUDE.md files become part of Claude's prompts, so they should be refined like any frequently used prompt." - Claude Code Documentation

### Setup Strategy

1. **Add file structure** with descriptions

   - List major entry points for each file
   - Describe what each component does

2. **Create hierarchical CLAUDE.md files**

   - Main CLAUDE.md at root
   - Sub-folder CLAUDE.md files for major directories
   - Claude will fetch relevant sub-folder files based on context

3. **Use memories** - The `/memory` command helps add context more easily

### CLAUDE.md Content Ideas

**MCP Configuration:**

```markdown
## Available MCPs

- GitHub: For repository operations
- Playwright: For browser automation
- Context7: For documentation lookup
```

**Design Principles:**

- Use Deep Research to generate `design-principles.md`
- Reference external style guides (e.g., "Conventional Commits", "Airbnb JS Style Guide")

### Other Useful .md Files

| File              | Purpose                 |
| ----------------- | ----------------------- |
| `CHANGELOG.md`    | Track major updates     |
| `plan.md`         | Large project planning  |
| Development notes | Keep track of decisions |

---

## When to Use Claude Code vs. Other Tools

### Use Claude Code For

- Multi-step processes
- Starting new projects
- Complex tasks
- Long-running operations
- Exploring/ramping up on codebases
- Refactoring large files
- Generating files requiring info from many sources (README, Postman collections)
- Generating tests with feedback loops

### Use Cursor/Other IDE Tools For

- Specific problems in specific files/lines
- One-step tasks
- Managed, incremental development
- Fine-grained control over edits

---

## Common Struggles and Solutions

| Problem                                          | Solution                        |
| ------------------------------------------------ | ------------------------------- |
| Managing edits and changes                       | Use git, or trust the agent     |
| "Abuses grep" - keeps searching for known things | Well-structured CLAUDE.md files |
| Context window limits                            | Use sub-agents to summarize     |

---

## Essential Commands

| Command    | Use Case                           |
| ---------- | ---------------------------------- |
| `/model`   | Switch between Sonnet 4 and Opus 4 |
| `/add-dir` | Add directory context              |
| `/memory`  | Add memories to CLAUDE.md          |
| `/plan`    | Enter planning mode                |
| `/clear`   | Clear context                      |

---

## Planning and Sub-agents

### Planning Mode

- Use before complex tasks
- Think through execution steps
- Creates structured approach

### Sub-agents

- Spawn for specific sub-tasks
- Summarize large contexts
- Parallel execution capabilities

---

## Multi-Agent Workflows

### Git Worktrees for Parallel Development

```bash
git worktree add <PATH> <BRANCH-NAME>
git worktree list
```

This enables running multiple Claude Code instances on different branches simultaneously.

### Claude Code + GitHub Actions

- Run up to 30 agents at once
- Async deployment of Claude Code
- CI/CD integration for autonomous work

---

## Beyond Engineering

Claude Code can handle non-coding tasks:

- **Second Brain** management
- **Computer Admin** - naming screenshots, organizing files, pipe operations
- **YouTube summary** + execution of tutorials
- **Image manipulation**, 3D modeling
- **Building slide decks**
- **Workflow automations** (e.g., n8n + headless Claude Code)

---

## MCP Servers

### Types

| Type                  | Examples                                                    |
| --------------------- | ----------------------------------------------------------- |
| **Local**             | Playwright, Sequential Thinking, browser-tools-mcp, Blender |
| **Remote**            | GitHub, FireCrawl, Sentry                                   |
| **Platform-specific** | Gemini Apps, Anthropic Partners                             |
| **Custom**            | For logic encapsulation                                     |

### Go-To MCPs for Coding

1. **GitHub** (or via CLI)
2. **Playwright** - browser automation
3. **Context7** - documentation lookup
4. **FireCrawl** - web scraping
5. **Markitdown** - document conversion
6. **Notion** - note integration

### MCP Registries

- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- [Cline Marketplace](https://cline.bot/mcp-marketplace)
- [Cursor Directory](https://cursor.directory/mcp)
- [Smithery](https://smithery.ai/)
- [Anthropic Partners](https://www.anthropic.com/partners/mcp)

---

## The Future: Orchestration Mindset

> "We need to get comfortable delegating. Build the system that 'compiles' into the code. Your 'spec' is your new 'source code'." - Patrick Ellis

Key shifts:

- Think of prompts and specs as source code
- Design for agent orchestration
- Delegate confidently to sub-agents

---

## Final Tips

1. **Use Claude as an independent agent** - a "super sidekick"
2. **Plan before executing** - use plan mode or external plan files
3. **Maximize context** - CLAUDE.md, commands, MCPs
4. **Use GitHub integration** for multi-agent, async deployment
5. **Keep everything in model context** - use sub-agents to summarize when needed

---

## Resources

### Official Anthropic

- [Mastering Claude Code in 30 minutes](https://www.youtube.com/watch?v=6eBSHbLKuN0)
- [Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Engineering at Anthropic Blog](https://www.anthropic.com/engineering)
- [Anthropic YouTube](https://www.youtube.com/@AnthropicAI)

### Community Resources

- [Claude Code Commands Directory](https://claudecodecommands.directory)
- [Latent Space Podcast](https://www.latent.space/podcast)
- [AI Engineer YouTube](https://www.youtube.com/@aiDotEngineer)
- [AI Daily Brief](https://www.youtube.com/@AIDailyBrief)
- [AI News Aggregator](https://news.smol.ai/)

### Key People to Follow (X/Twitter)

- [@alexalbert\_\_](https://x.com/alexalbert__) - Claude PM
- [@\_catwu](https://x.com/_catwu)
- [@trq212](https://x.com/trq212)
- [@googleaidevs](https://x.com/googleaidevs)
- [@OfficialLoganK](https://x.com/OfficialLoganK)

---

_Synthesized from presentations by Patrick Ellis (patrickellis.io) and Anand Tyagi, 2025._
