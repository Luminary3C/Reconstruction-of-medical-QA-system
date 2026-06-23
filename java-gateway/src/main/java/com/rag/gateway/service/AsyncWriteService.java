package com.rag.gateway.service;

import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

@Service
public class AsyncWriteService {

    private final RedisService redisService;

    public AsyncWriteService(RedisService redisService) {
        this.redisService = redisService;
    }

    /** 流结束后触发：Redis 滑动窗口追加。PG 持久化由 Python Agent 异步 _post_process 负责（带 embedding）。 */
    @Async
    public void persistConversation(String userId, String sessionId,
                                     String question, String answer) {
        redisService.pushMessage(userId, "Q: " + question + " | A: " + answer);
    }
}