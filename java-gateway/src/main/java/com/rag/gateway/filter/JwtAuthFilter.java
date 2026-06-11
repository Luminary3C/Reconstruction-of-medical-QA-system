package com.rag.gateway.filter;

import com.rag.gateway.service.RedisService;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.crypto.SecretKey;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;

@Component
public class JwtAuthFilter extends OncePerRequestFilter {

    private final RedisService redisService;
    private final SecretKey key;

    public JwtAuthFilter(RedisService redisService,
                         @Value("${jwt.secret}") String secret) {
        this.redisService = redisService;
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String path = request.getRequestURI();
        if (path.startsWith("/api/v1/auth/") || path.startsWith("/actuator") || path.startsWith("/mcp/")) {
            chain.doFilter(request, response);
            return;
        }

        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            // 不直接写 response，交给 Spring Security 的异常处理机制
            chain.doFilter(request, response);
            return;
        }

        try {
            String token = authHeader.substring(7);
            Claims claims = Jwts.parser()
                    .verifyWith(key)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();

            String userIdStr = claims.getSubject();
            Long userId = Long.parseLong(userIdStr);

            if (!redisService.isTokenValid(userId, token)) {
                chain.doFilter(request, response);
                return;
            }

            // 注入 SecurityContext（赋予 USER 角色）
            UsernamePasswordAuthenticationToken auth =
                    new UsernamePasswordAuthenticationToken(
                            userIdStr, null,
                            List.of(new SimpleGrantedAuthority("ROLE_USER")));
            SecurityContextHolder.getContext().setAuthentication(auth);

            List<String> recentMessages = redisService.getRecentMessages(userIdStr);
            request.setAttribute("shortTermContext", recentMessages);
            request.setAttribute("userId", userIdStr);

        } catch (Exception e) {
            // JWT 解析失败，不写 response，让 Security 框架统一处理
            chain.doFilter(request, response);
            return;
        }

        chain.doFilter(request, response);
    }
}
