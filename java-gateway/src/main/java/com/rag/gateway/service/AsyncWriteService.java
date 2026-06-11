package com.rag.gateway.service;

import com.rag.gateway.config.RabbitMQConfig;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class AsyncWriteService {

    private final RedisService redisService;
    private final RabbitTemplate rabbitTemplate;

    public AsyncWriteService(RedisService redisService, RabbitTemplate rabbitTemplate) {
        this.redisService = redisService;
        this.rabbitTemplate = rabbitTemplate;
    }

    /** 流结束后触发：Redis 追加 + MQ 消息。调用后业务线程立即释放。 */
    @Async
    public void persistConversation(String userId, String sessionId,
                                     String question, String answer) {
        // 1. Redis 追加 + 保持滑动窗口 5 轮
        redisService.pushMessage(userId, "Q: " + question + " | A: " + answer);

        // 2. RabbitMQ publish — 消费者负责 embedding + PGSQL 写入
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("userId", userId);
        payload.put("sessionId", sessionId);
        payload.put("question", question);
        payload.put("answer", answer);
        payload.put("createdAt", LocalDateTime.now().toString());
        rabbitTemplate.convertAndSend(RabbitMQConfig.CHAT_EXCHANGE, "chat.persistence", payload);
    }
}