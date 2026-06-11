package com.rag.gateway.mcp;

import com.rag.gateway.dto.ApiResponse;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Unified MCP HTTP endpoint for Memory, User, Audit servers.
 * Python Agent calls these as MCP Tool/Resource invocations over HTTP.
 */
@RestController
@RequestMapping("/mcp")
public class MCPController {

    private final MemoryToolHandler memoryHandler;
    private final UserResourceHandler userHandler;
    private final AuditToolHandler auditHandler;

    public MCPController(MemoryToolHandler memoryHandler,
                         UserResourceHandler userHandler,
                         AuditToolHandler auditHandler) {
        this.memoryHandler = memoryHandler;
        this.userHandler = userHandler;
        this.auditHandler = auditHandler;
    }

    // ── Memory Server Tools ──────────────────────

    @PostMapping("/memory/tools/search_long_term_memory")
    public ApiResponse<?> searchLongTermMemory(@RequestBody Map<String, Object> body) {
        return memoryHandler.searchLongTermMemory(body);
    }

    @PostMapping("/memory/tools/save_conversation")
    public ApiResponse<?> saveConversation(@RequestBody Map<String, Object> body) {
        return memoryHandler.saveConversation(body);
    }

    @PostMapping("/memory/tools/summarize_history")
    public ApiResponse<?> summarizeHistory(@RequestBody Map<String, Object> body) {
        return memoryHandler.summarizeHistory(body);
    }

    // ── User Server Resources ────────────────────

    @GetMapping("/user/resources/user/{userId}/profile")
    public ApiResponse<?> getUserProfile(@PathVariable String userId) {
        return userHandler.getProfile(userId);
    }

    @GetMapping("/user/resources/user/{userId}/permissions")
    public ApiResponse<?> getUserPermissions(@PathVariable String userId) {
        return userHandler.getPermissions(userId);
    }

    // ── Audit Server Tools ───────────────────────

    @PostMapping("/audit/tools/audit_log")
    public ApiResponse<?> auditLog(@RequestBody Map<String, Object> body) {
        return auditHandler.auditLog(body);
    }
}