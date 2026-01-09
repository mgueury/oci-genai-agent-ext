package orcldbsee; 

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository; 

import java.sql.Timestamp;
import java.time.Instant; 

@Repository
public class SseDataRepository { 
private final JdbcTemplate jdbcTemplate;

public SseDataRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
}

public void insertEvent(String threadId, String eventId, String eventName, String eventData) {
    String sql = "INSERT INTO SSE_DATA (THREAD_ID, EVENT_ID, EVENT_NAME, EVENT_DATA, CREATEDATE) VALUES (?,?,?,?,?)";
    jdbcTemplate.update(sql,
            threadId,
            eventId,
            eventName,
            eventData,
            Timestamp.from(Instant.now()));
}

} 