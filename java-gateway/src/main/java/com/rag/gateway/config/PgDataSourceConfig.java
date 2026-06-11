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
import org.springframework.jdbc.datasource.DataSourceTransactionManager;

import javax.sql.DataSource;

@Configuration
@MapperScan(
    basePackages = "com.rag.gateway.repository.pg",
    sqlSessionFactoryRef = "pgSessionFactory"
)
public class PgDataSourceConfig {

    @Bean(name = "pgDataSource")
    public DataSource pgDataSource(
            @Value("${spring.datasource.pg.url}") String url,
            @Value("${spring.datasource.pg.username}") String username,
            @Value("${spring.datasource.pg.password}") String password,
            @Value("${spring.datasource.pg.driver-class-name}") String driver) {
        return DataSourceBuilder.create()
                .type(HikariDataSource.class)
                .url(url)
                .username(username)
                .password(password)
                .driverClassName(driver)
                .build();
    }

    @Bean(name = "pgTransactionManager")
    public DataSourceTransactionManager pgTransactionManager(
            @Qualifier("pgDataSource") DataSource ds) {
        return new DataSourceTransactionManager(ds);
    }

    @Bean(name = "pgSessionFactory")
    public SqlSessionFactory pgSessionFactory(
            @Qualifier("pgDataSource") DataSource ds) throws Exception {
        SqlSessionFactoryBean bean = new SqlSessionFactoryBean();
        bean.setDataSource(ds);
        bean.setTypeAliasesPackage("com.rag.gateway.model");
        org.apache.ibatis.session.Configuration config = new org.apache.ibatis.session.Configuration();
        config.setMapUnderscoreToCamelCase(true);
        bean.setConfiguration(config);
        return bean.getObject();
    }
}
