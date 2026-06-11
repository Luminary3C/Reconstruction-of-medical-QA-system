package com.rag.gateway.dto;

import java.util.UUID;

public class ApiResponse<T> {

    private int code;
    private String msg;
    private T data;
    private String traceId;

    public ApiResponse() {
        this.traceId = UUID.randomUUID().toString();
    }

    public static <T> ApiResponse<T> success(T data) {
        ApiResponse<T> resp = new ApiResponse<>();
        resp.code = 200;
        resp.msg = "success";
        resp.data = data;
        return resp;
    }

    public static <T> ApiResponse<T> error(int code, String msg) {
        ApiResponse<T> resp = new ApiResponse<>();
        resp.code = code;
        resp.msg = msg;
        return resp;
    }

    public int getCode() { return code; }
    public void setCode(int code) { this.code = code; }
    public String getMsg() { return msg; }
    public void setMsg(String msg) { this.msg = msg; }
    public T getData() { return data; }
    public void setData(T data) { this.data = data; }
    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
}
