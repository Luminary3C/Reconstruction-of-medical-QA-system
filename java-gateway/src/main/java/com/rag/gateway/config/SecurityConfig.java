package com.rag.gateway.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.rag.gateway.dto.ApiResponse;
import com.rag.gateway.filter.JwtAuthFilter;
import com.rag.gateway.filter.RateLimitFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import jakarta.servlet.DispatcherType;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.intercept.AuthorizationFilter;

@Configuration
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;
    private final RateLimitFilter rateLimitFilter;
    private final ObjectMapper objectMapper;

    public SecurityConfig(JwtAuthFilter jwtAuthFilter, RateLimitFilter rateLimitFilter, ObjectMapper objectMapper) {
        this.jwtAuthFilter = jwtAuthFilter;
        this.rateLimitFilter = rateLimitFilter;
        this.objectMapper = objectMapper;
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .dispatcherTypeMatchers(DispatcherType.ASYNC, DispatcherType.ERROR).permitAll()
                .requestMatchers("/actuator/health", "/error", "/mcp/**", "/api/v1/auth/**").permitAll()
                .requestMatchers("/api/v1/**").hasRole("USER")
                .anyRequest().denyAll()
            )
            .exceptionHandling(eh -> eh
                .authenticationEntryPoint((req, res, ex) -> {
                    res.setStatus(401);
                    res.setContentType("application/json;charset=UTF-8");
                    res.getWriter().write(objectMapper.writeValueAsString(
                            ApiResponse.error(401, "unauthorized")));
                })
                .accessDeniedHandler((req, res, ex) -> {
                    res.setStatus(403);
                    res.setContentType("application/json;charset=UTF-8");
                    res.getWriter().write(objectMapper.writeValueAsString(
                            ApiResponse.error(403, "access denied")));
                })
            )
            .addFilterBefore(jwtAuthFilter, AuthorizationFilter.class)
            .addFilterAfter(rateLimitFilter, JwtAuthFilter.class);
        return http.build();
    }
}
