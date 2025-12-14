package orcldbsee;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository; 

import java.util.UUID; 

@Repository
public class SseEventRepository { 
private final JdbcTemplate jdbcTemplate;

public SseEventRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
}

public int currentMaxOrderForThread(String threadId) {
    Integer max = jdbcTemplate.queryForObject(
            "SELECT COALESCE(MAX(EVENT_ORDER),0) FROM SSE_EVENTS WHERE THREAD_ID = ?",
            Integer.class,
            threadId
    );
    return (max == null) ? 0 : max;
}

public void insertEvent(String sseId,
                        String threadId,
                        int eventOrder,
                        String eventName,
                        String finishReason,
                        String dataContent,
                        String fullData) {
    jdbcTemplate.update(con -> {
        var ps = con.prepareStatement(
            "INSERT INTO SSE_EVENTS " +
            "(SSE_ID, THREAD_ID, EVENT_ORDER, EVENT_NAME, FINISH_REASON, CREATEDATE, DATA_CONTENT, FULL_DATA) " +
            "VALUES (?, ?, ?, ?, ?, SYSTIMESTAMP, ?, ?)"
        );
        ps.setString(1, sseId != null ? sseId : UUID.randomUUID().toString());
        ps.setString(2, threadId);
        ps.setInt(3, eventOrder);
        ps.setString(4, eventName);
        ps.setString(5, finishReason);
        ps.setString(6, dataContent);
        ps.setString(7, fullData);
        return ps;
    });
}

} 