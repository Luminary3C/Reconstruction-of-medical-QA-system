package com.rag.gateway.controller;

import com.rag.gateway.dto.ApiResponse;
import com.rag.gateway.dto.SessionSummary;
import com.rag.gateway.model.ChatMessage;
import com.rag.gateway.repository.pg.ChatMessageMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/chat")
public class ChatHistoryController {

    private final ChatMessageMapper mapper;

    public ChatHistoryController(ChatMessageMapper mapper) {
        this.mapper = mapper;
    }

    @GetMapping("/sessions")
    public ApiResponse<List<SessionSummary>> getSessions(HttpServletRequest request) {
        String userId = (String) request.getAttribute("userId");
        List<SessionSummary> sessions = mapper.findSessionsByUserId(userId);
        return ApiResponse.success(sessions);
    }

    @GetMapping("/history/{sessionId}")
    public ApiResponse<List<ChatMessage>> getHistory(@PathVariable String sessionId) {
        List<ChatMessage> messages = mapper.findBySessionId(sessionId);
        return ApiResponse.success(messages);
    }

    @DeleteMapping("/history/{sessionId}")
    public ApiResponse<Void> deleteHistory(@PathVariable String sessionId) {
        mapper.deleteBySessionId(sessionId);
        return ApiResponse.success(null);
    }
}