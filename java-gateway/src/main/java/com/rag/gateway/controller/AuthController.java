package com.rag.gateway.controller;

import com.rag.gateway.dto.ApiResponse;
import com.rag.gateway.model.User;
import com.rag.gateway.repository.mysql.UserMapper;
import com.rag.gateway.service.RedisService;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.*;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final UserMapper userMapper;
    private final RedisService redisService;
    private final BCryptPasswordEncoder passwordEncoder;
    private final SecretKey key;
    private final long expiration;

    public AuthController(UserMapper userMapper,
                          RedisService redisService,
                          @Value("${jwt.secret}") String secret,
                          @Value("${jwt.expiration:86400000}") long expiration) {
        this.userMapper = userMapper;
        this.redisService = redisService;
        this.passwordEncoder = new BCryptPasswordEncoder();
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expiration = expiration;
    }

    @PostMapping("/login")
    public ApiResponse<Map<String, String>> login(@RequestBody Map<String, String> body) {
        String username = body.get("username");
        if (username == null || username.isBlank()) {
            username = body.get("userId"); // 兼容旧字段名
        }
        String password = body.get("password");

        if (username == null || username.isBlank()) {
            return ApiResponse.error(400, "username is required");
        }
        if (password == null || password.isBlank()) {
            return ApiResponse.error(400, "password is required");
        }

        // 1. 根据用户名查询 MySQL
        User user = userMapper.findByUsername(username);
        if (user == null) {
            return ApiResponse.error(401, "用户名或密码错误");
        }

        // 2. BCrypt 密码匹配校验
        if (!passwordEncoder.matches(password, user.getPasswordHash())) {
            return ApiResponse.error(401, "用户名或密码错误");
        }

        // 3. 生成 JWT Token
        String token = Jwts.builder()
                .subject(String.valueOf(user.getId()))
                .claim("username", user.getUsername())
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + expiration))
                .signWith(key)
                .compact();

        // 4. 将 Token 保存到 Redis，设置过期时间
        redisService.saveToken(user.getId(), token, expiration, TimeUnit.MILLISECONDS);

        return ApiResponse.success(Map.of(
                "token", token,
                "userId", String.valueOf(user.getId()),
                "username", user.getUsername()
        ));
    }
}
