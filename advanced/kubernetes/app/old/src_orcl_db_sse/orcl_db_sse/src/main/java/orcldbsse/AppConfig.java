package orcldbsee; 

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient; 

import javax.sql.DataSource;
import java.time.Duration; 

@Configuration
public class AppConfig { 
@Value("${LANGGRAPH_URL:}")
private String langGraphUrl;

@Value("${JDBC_URL:}")
private String jdbcUrl;

@Value("${DB_USER:}")
private String dbUser;

@Value("${DB_PASSWORD:}")
private String dbPassword;

@Bean
public WebClient langGraphWebClient() {
    return WebClient.builder()
            .baseUrl(langGraphUrl)
            .clientConnector(new ReactorClientHttpConnector())
            .build();
}

@Bean
public DataSource dataSource() {
    HikariConfig cfg = new HikariConfig();
    cfg.setJdbcUrl(jdbcUrl);
    cfg.setUsername(dbUser);
    cfg.setPassword(dbPassword);
    // Reasonable defaults; tune for prod
    cfg.setMaximumPoolSize(10);
    cfg.setMinimumIdle(1);
    cfg.setConnectionTimeout(15000);
    cfg.setIdleTimeout(600000);
    return new HikariDataSource(cfg);
}

} 