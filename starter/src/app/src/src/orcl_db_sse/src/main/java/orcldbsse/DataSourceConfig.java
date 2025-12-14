package orcldbsee;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.sql.DataSource;

@Configuration
public class DataSourceConfig {
    @Bean
    public DataSource dataSource() {
        String jdbcUrl = System.getenv("JDBC_URL");
        String dbUser = System.getenv("DB_USER");
        String dbPassword = System.getenv("DB_PASSWORD");

        if (jdbcUrl == null || dbUser == null || dbPassword == null) {
            throw new IllegalStateException("Environment variables JDBC_URL, DB_USER, and DB_PASSWORD must be set.");
        }

        HikariConfig cfg = new HikariConfig();
        cfg.setJdbcUrl(jdbcUrl);
        cfg.setUsername(dbUser);
        cfg.setPassword(dbPassword);
        // Reasonable defaults; tune as needed
        cfg.setMaximumPoolSize(10);
        cfg.setMinimumIdle(1);
        cfg.setPoolName("sse-events-pool");
        // Oracle recommended driver class is auto-detected; can be set explicitly if
        // desired:
        // cfg.setDriverClassName("oracle.jdbc.OracleDriver");
        return new HikariDataSource(cfg);
    }
}