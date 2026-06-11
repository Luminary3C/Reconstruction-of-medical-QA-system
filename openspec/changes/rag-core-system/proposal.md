# Proposal: RAG Core System

## Summary

从零搭建 RAG 智能问答系统的核心骨架：Java SpringBoot API 网关 + Python FastAPI 推理引擎 + 三路并行召回 + 全链路异步流式 + 异步双写持久化。

## Motivation

docs 文档定义了完整的技术方案：业务算法分离（Java 工程 / Python AI）、三路召回（短期记忆 + 知识库 + 长期记忆）、全链路流式优化 TTFT。需要将文档中的设计落地为可执行任务。

## Scope

### In scope
- Java SpringBoot API 网关：JWT 鉴权、Redis 短期上下文、SSE 流式透传、StringBuilder 答案拼装
- Python FastAPI Agent：三路并行召回、上下文融合、LLM 流式推理
- 基础设施 (Docker)：PostgreSQL pgvector (5432:5432) + Redis (6379:6379)
- RabbitMQ 异步削峰：对话异步写回 PostgreSQL
- RESTful API 统一规范：分层架构 (Controller/Service/Repository)
- 配置管理：12-Factor App, 环境变量注入

### Non-goals
- MCP 插件化（后续 change `mcp-plugin-architecture` 覆盖）
- vLLM 集群 / GPU 调度
- Kafka 替代 RabbitMQ
- 向量库独立集群（MVP 阶段用 pgvector 一把梭）

## Impact

- 新建项目，无存量代码影响
- 建立 Java + Python 双语言工程规范
- 为本项目后续所有 change 提供基础设施基线

## Dependencies

- Docker Desktop (Windows), Python 3.11+, Java 17+, Maven/Gradle