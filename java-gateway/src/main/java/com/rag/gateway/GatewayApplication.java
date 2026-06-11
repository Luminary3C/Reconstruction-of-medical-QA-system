package com.rag.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication(exclude = {
    org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration.class,
    org.mybatis.spring.boot.autoconfigure.MybatisAutoConfiguration.class
})
@EnableAsync
public class GatewayApplication {

    public static void main(String[] args) {
        // 让 SecurityContext 跨线程传递（SseEmitter 异步派发时 ThreadLocal 会丢失）
        System.setProperty("spring.security.strategy", "MODE_INHERITABLETHREADLOCAL");
        SpringApplication.run(GatewayApplication.class, args);
    }
}
