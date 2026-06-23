package com.rag.gateway.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Service
public class PythonAgentClient {

    private static final Logger log = LoggerFactory.getLogger(PythonAgentClient.class);
    private final String agentUrl;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;
    private final ExecutorService executor = Executors.newCachedThreadPool();

    public PythonAgentClient(@Value("${agent.python.url}") String agentUrl, ObjectMapper objectMapper) {
        this.agentUrl = agentUrl;
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(15))
                .build();
    }

    /**
     * 流式调用 Python Agent，将 SSE token 逐个推送到 SseEmitter。
     * 返回完整回答文本。
     */
    public CompletableFuture<String> streamChat(String userMessage, String userId, String sessionId,
                                                 List<String> shortTermContext, SseEmitter emitter) {
        CompletableFuture<String> future = new CompletableFuture<>();

        executor.submit(() -> {
            StringBuilder fullAnswer = new StringBuilder();
            try {
                Map<String, Object> message = new LinkedHashMap<>();
                message.put("role", "user");
                message.put("content", userMessage);

                Map<String, Object> body = new LinkedHashMap<>();
                body.put("messages", List.of(message));
                body.put("stream", true);
                body.put("user_id", userId);
                body.put("session_id", sessionId);
                body.put("short_term_context", shortTermContext != null ? shortTermContext : List.of());

                String jsonBody = objectMapper.writeValueAsString(body);

                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(agentUrl + "/v1/chat/completions"))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                        .timeout(Duration.ofMinutes(3))
                        .build();

                HttpResponse<java.util.stream.Stream<String>> response = httpClient.send(
                        request, HttpResponse.BodyHandlers.ofLines());

                response.body().forEach(line -> {
                    String trimmed = line.trim();
                    if (!trimmed.startsWith("data:") || trimmed.equals("data: [DONE]")) {
                        return;
                    }
                    String jsonStr = trimmed.substring(5).trim();
                    if (jsonStr.isEmpty()) return;

                    try {
                        JsonNode node = objectMapper.readTree(jsonStr);

                        // Check for verification event from Python Agent
                        if ("verification".equals(node.path("type").asText())) {
                            emitter.send(SseEmitter.event().name("verification").data(jsonStr));
                            return;
                        }

                        JsonNode content = node.at("/choices/0/delta/content");
                        if (!content.isMissingNode() && !content.isNull()) {
                            String token = content.asText();
                            fullAnswer.append(token);
                            emitter.send(SseEmitter.event().data(token));
                        }
                    } catch (Exception parseEx) {
                        log.debug("Skipping non-JSON SSE line: {}", trimmed);
                    }
                });

                future.complete(fullAnswer.toString());
            } catch (Exception e) {
                log.error("Python Agent stream error: {}", e.getMessage());
                future.completeExceptionally(e);
            }
        });

        return future;
    }
}
