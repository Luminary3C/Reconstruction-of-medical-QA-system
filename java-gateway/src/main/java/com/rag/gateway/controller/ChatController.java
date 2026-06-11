package com.rag.gateway.controller;

import com.rag.gateway.dto.ChatRequest;
import com.rag.gateway.service.AsyncWriteService;
import com.rag.gateway.service.PythonAgentClient;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/chat")
public class ChatController {

    private final PythonAgentClient agentClient;
    private final AsyncWriteService asyncWriteService;

    public ChatController(PythonAgentClient agentClient, AsyncWriteService asyncWriteService) {
        this.agentClient = agentClient;
        this.asyncWriteService = asyncWriteService;
    }

    @PostMapping(value = "/ask", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chat(@Valid @RequestBody ChatRequest req, HttpServletRequest request) {
        SseEmitter emitter = new SseEmitter(180_000L);

        @SuppressWarnings("unchecked")
        List<String> shortTermContext =
                (List<String>) request.getAttribute("shortTermContext");
        String userId = (String) request.getAttribute("userId");
        String sessionId = req.getSessionId() != null ? req.getSessionId() : UUID.randomUUID().toString();

        agentClient.streamChat(req.getMessage(), userId, sessionId, shortTermContext, emitter)
                .whenComplete((fullAnswer, error) -> {
                    if (error != null) {
                        try { emitter.completeWithError(error); } catch (Exception ignored) {}
                    } else {
                        if (fullAnswer != null && !fullAnswer.isEmpty()) {
                            asyncWriteService.persistConversation(userId, sessionId, req.getMessage(), fullAnswer);
                        }
                        emitter.complete();
                    }
                });

        return emitter;
    }
}
