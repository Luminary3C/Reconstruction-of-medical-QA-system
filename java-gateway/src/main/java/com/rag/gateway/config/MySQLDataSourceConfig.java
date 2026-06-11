package com.rag.gateway.config;

import com.zaxxer.hikari.HikariDataSource;
import org.apache.ibatis.session.SqlSessionFactory;
import org.mybatis.spring.SqlSessionFactoryBean;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.jdbc.DataSourceBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;

import javax.sql.DataSource;

@Configuration
@MapperScan(
    basePackages = "com.rag.gateway.repository.mysql",
    sqlSessionFactoryRef = "mysqlSessionFactory"
)
public class MySQLDataSourceConfig {

    @Primary
    @Bean(name = "mysqlDataSource")
    public DataSource mysqlDataSource(
            @Value("${spring.datasource.mysql.url}") String url,
            @Value("${spring.datasource.mysql.username}") String username,
            @Value("${spring.datasource.mysql.password}") String password,
            @Value("${spring.datasource.mysql.driver-class-name}") String driver) {
        return DataSourceBuilder.create()
                .type(HikariDataSource.class)
                .url(url)
                .username(username)
                .password(password)
                .driverClassName(driver)
                .build();
    }

    @Primary
    @Bean(name = "mysqlTransactionManager")
    public DataSourceTransactionManager mysqlTransactionManager(
            @Qualifier("mysqlDataSource") DataSource ds) {
        return new DataSourceTransactionManager(ds);
    }

    @Primary
    @Bean(name = "mysqlSessionFactory")
    public SqlSessionFactory mysqlSessionFactory(
            @Qualifier("mysqlDataSource") DataSource ds) throws Exception {
        SqlSessionFactoryBean bean = new SqlSessionFactoryBean();
        bean.setDataSource(ds);
        bean.setTypeAliasesPackage("com.rag.gateway.model");
        org.apache.ibatis.session.Configuration config = new org.apache.ibatis.session.Configuration();
        config.setMapUnderscoreToCamelCase(true);
        bean.setConfiguration(config);
        return bean.getObject();
    }
}
