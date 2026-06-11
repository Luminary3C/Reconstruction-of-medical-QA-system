package com.rag.gateway.mcp;

import com.rag.gateway.config.RabbitMQConfig;
import com.rag.gateway.dto.ApiResponse;
import com.rag.gateway.model.ChatMessage;
import com.rag.gateway.repository.pg.ChatMessageMapper;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Component
public class MemoryToolHandler {

    private final ChatMessageMapper mapper;
    private final RabbitTemplate rabbitTemplate;

    public MemoryToolHandler(ChatMessageMapper mapper, RabbitTemplate rabbitTemplate) {
        this.mapper = mapper;
        this.rabbitTemplate = rabbitTemplate;
    }

    /** 长期记忆检索 — pgvector 语义相似度搜索 */
    public ApiResponse<?> searchLongTermMemory(Map<String, Object> body) {
        String query = (String) body.get("query");
        String userId = (String) body.get("user_id");
        int topK = body.get("top_k") instanceof Integer i ? i : 10;

        String embedding = (String) body.get("embedding");

        List<ChatMessage> results;
        if (embedding != null && !embedding.isBlank()) {
            try {
                results = mapper.findSimilarByEmbedding(userId, embedding, topK);
            } catch (Exception e) {
                results = List.of();
            }
        } else {
            // 无 embedding 时走文本搜索（兼容）
            results = mapper.findByKeyword(userId, query, topK);
        }

        List<Map<String, Object>> compressed = results.stream().map(r -> {
            String summary = r.getAnswer() != null && r.getAnswer().length() > 200
                    ? r.getAnswer().substring(0, 200) + "..."
                    : r.getAnswer();
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("memory_id", r.getId().toString());
            entry.put("content", "Q: " + r.getQuestion() + " | A: " + summary);
            entry.put("score", 0.0);
            entry.put("timestamp", r.getCreatedAt() != null ? r.getCreatedAt().toString() : "");
            return entry;
        }).collect(Collectors.toList());

        return ApiResponse.success(compressed);
    }

    /** 异步持久化: write MQ → MyBatis → pgvector (fire & forget). */
    public ApiResponse<?> saveConversation(Map<String, Object> body) {
        String userId = (String) body.get("user_id");
        String question = (String) body.get("question");
        String answer = (String) body.get("answer");
        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) body.getOrDefault("metadata", new HashMap<>());

        String embedding = (String) body.get("embedding");

        String conversationId = UUID.randomUUID().toString();

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("userId", userId);
        payload.put("sessionId", metadata.getOrDefault("session_id", conversationId));
        payload.put("question", question);
        payload.put("answer", answer);
        payload.put("createdAt", LocalDateTime.now().toString());
        if (embedding != null && !embedding.isBlank()) {
            payload.put("embedding", embedding);
        }

        rabbitTemplate.convertAndSend(RabbitMQConfig.CHAT_EXCHANGE, "chat.persistence", payload);

        Map<String, Object> result = new HashMap<>();
        result.put("conversation_id", conversationId);
        return ApiResponse.success(result);
    }

    public ApiResponse<?> summarizeHistory(Map<String, Object> body) {
        Map<String, Object> result = new HashMap<>();
        result.put("summary", "TBD");
        return ApiResponse.success(result);
    }
}