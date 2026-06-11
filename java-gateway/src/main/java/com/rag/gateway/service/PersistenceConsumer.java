package com.rag.gateway.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.rag.gateway.config.RabbitMQConfig;
import com.rag.gateway.model.ChatMessage;
import com.rag.gateway.repository.pg.ChatMessageMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;

@Component
public class PersistenceConsumer {

    private static final Logger log = LoggerFactory.getLogger(PersistenceConsumer.class);
    private final ChatMessageMapper mapper;
    private final ObjectMapper objectMapper;

    public PersistenceConsumer(ChatMessageMapper mapper, ObjectMapper objectMapper) {
        this.mapper = mapper;
        this.objectMapper = objectMapper;
    }

    @RabbitListener(queues = RabbitMQConfig.CHAT_QUEUE)
    public void consume(Message message) {
        try {
            String rawJson = new String(message.getBody(), StandardCharsets.UTF_8);
            JsonNode root = objectMapper.readTree(rawJson);

            String userId = root.path("userId").asText();
            String sessionId = root.path("sessionId").asText();
            String question = root.path("question").asText();

            JsonNode answerNode = root.path("answer");
            String answer = answerNode.isTextual() ? answerNode.asText() : answerNode.toString();

            JsonNode embeddingNode = root.path("embedding");
            String embedding = embeddingNode.isTextual() ? embeddingNode.asText() : null;

            log.info("Persisting conversation: userId={}, sessionId={}, answerLen={}, hasEmbedding={}",
                    userId, sessionId, answer.length(), embedding != null && !embedding.isBlank());

            if (embedding != null && !embedding.isBlank()) {
                mapper.insertWithEmbedding(userId, sessionId, question, answer, embedding);
            } else {
                ChatMessage msg = new ChatMessage();
                msg.setUserId(userId);
                msg.setSessionId(sessionId);
                msg.setQuestion(question);
                msg.setAnswer(answer);
                mapper.insert(msg);
            }
        } catch (Exception e) {
            log.error("Failed to process/persist message: {}", e.getMessage());
            throw new AmqpRejectAndDontRequeueException(e);
        }
    }

    @RabbitListener(queues = RabbitMQConfig.CHAT_DLQ)
    public void consumeDlq(Message message) {
        String raw = new String(message.getBody(), StandardCharsets.UTF_8);
        log.error("Message in DLQ: {} chars", raw.length());
    }
}