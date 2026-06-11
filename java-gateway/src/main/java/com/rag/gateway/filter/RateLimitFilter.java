package com.rag.gateway.filter;

import com.rag.gateway.service.RedisService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Set;

@Component
public class RateLimitFilter extends OncePerRequestFilter {

    private static final int MAX_BODY_SIZE = 10 * 1024; // 10KB

    private final RedisService redisService;

    public RateLimitFilter(RedisService redisService) {
        this.redisService = redisService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String userId = (String) request.getAttribute("userId");

        // IP 黑名单
        String clientIp = request.getRemoteAddr();

        // 用户级限流: 60s 内最多 30 次
        if (userId != null && redisService.isRateLimited(userId)) {
            response.setStatus(429);
            response.getWriter().write("{\"code\":429,\"msg\":\"rate limited\"}");
            return;
        }

        //  body 大小限制
        if (request.getContentLengthLong() > MAX_BODY_SIZE) {
            response.setStatus(413);
            response.getWriter().write("{\"code\":413,\"msg\":\"payload too large\"}");
            return;
        }

        chain.doFilter(request, response);
    }
}
