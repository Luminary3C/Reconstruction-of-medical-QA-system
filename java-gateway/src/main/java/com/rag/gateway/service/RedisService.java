package com.rag.gateway.service;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.TimeUnit;

@Service
public class RedisService {

    private final StringRedisTemplate redis;
    private static final int WINDOW_SIZE = 5;

    public RedisService(StringRedisTemplate redis) {
        this.redis = redis;
    }

    // ── Token 管理 ──────────────────────────────────────────────

    /** 登录后保存 Token */
    public void saveToken(Long userId, String token, long expiration, TimeUnit unit) {
        String key = "auth:token:" + userId;
        redis.opsForValue().set(key, token, expiration, unit);
    }

    /** 校验 Token 是否有效（与 Redis 中存储的一致） */
    public boolean isTokenValid(Long userId, String token) {
        String key = "auth:token:" + userId;
        String stored = redis.opsForValue().get(key);
        return token.equals(stored);
    }

    // ── 滑动窗口对话上下文 ──────────────────────────────────────

    /** 获取用户滑动窗口内的近期对话 */
    public List<String> getRecentMessages(String userId) {
        String key = "user:chat:" + userId + ":window";
        return redis.opsForList().range(key, 0, WINDOW_SIZE - 1);
    }

    /** 追加新对话到窗口(仅保留最近 WINDOW_SIZE 轮) */
    public void pushMessage(String userId, String message) {
        String key = "user:chat:" + userId + ":window";
        redis.opsForList().leftPush(key, message);
        redis.opsForList().trim(key, 0, WINDOW_SIZE - 1);
    }

    // ── 限流 ────────────────────────────────────────────────────

    /** 检查限流 */
    public boolean isRateLimited(String userId) {
        String key = "rate:user:" + userId + ":minute";
        Long count = redis.opsForValue().increment(key);
        if (count != null && count == 1) {
            redis.expire(key, java.time.Duration.ofSeconds(60));
        }
        return count != null && count > 30;
    }
}
