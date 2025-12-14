package orcldbsse;

import com.example.dto.StartSseRequest;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micronaut.context.annotation.Value;
import io.micronaut.http.MediaType;
import io.micronaut.http.MutableHttpRequest;
import io.micronaut.http.client.HttpClient;
import io.micronaut.http.client.annotation.Client;
import io.micronaut.http.client.sse.Event;
import io.micronaut.http.client.sse.SseClient;
import jakarta.inject.Inject;
import jakarta.inject.Singleton;

import javax.sql.DataSource;
import java.io.StringReader;
import java.sql.*;
import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;

@Singleton
public class SseIngestService {

    @Value("${LANGGRAPH_URL:env:LANGGRAPH_URL}")
    Optional<String> langgraphUrlEnv;

    private final SseClient sseClient;
    private final HttpClient httpClient;
    private final DataSource dataSource;
    private final ObjectMapper objectMapper;

    @Inject
    public SseIngestService(@Client("/") HttpClient httpClient, DataSource dataSource, ObjectMapper objectMapper) {
        this.httpClient = httpClient;
        this.sseClient = SseClient.create(httpClient);
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
    }

    public void startAndIngest(StartSseRequest req) {
        String sseUrl = langgraphUrlEnv.orElseGet(() -> System.getenv("LANGGRAPH_URL"));
        if (sseUrl == null || sseUrl.isBlank()) {
            throw new IllegalStateException("LANGGRAPH_URL is not set");
        }
        String streamId = UUID.randomUUID().toString();
        AtomicInteger order = new AtomicInteger(0);

        // Prepare the outbound request (POST with JSON body). Change to GET with query
        // params if needed.
        MutableHttpRequest<StartSseRequest> request = io.micronaut.http.HttpRequest.POST(sseUrl, req)
                .contentType(MediaType.APPLICATION_JSON_TYPE)
                .accept(MediaType.TEXT_EVENT_STREAM_TYPE);

        sseClient.eventStream(request, String.class).subscribe(event -> {
            try {
                handleEvent(streamId, order.incrementAndGet(), event);
            } catch (Exception e) {
                // Log and continue; you might want to cancel subscription on severe errors
                e.printStackTrace();
            }
        }, throwable -> {
            // Log SSE error
            throwable.printStackTrace();
        });

    }

    private void handleEvent(String streamId, int eventOrder, Event<String> event) throws Exception {
        String eventName = event.getName().orElse(null);
        String eventId = event.getId().orElse(streamId); // Prefer SSE's own id if present
        String data = event.getData();
        // Parse JSON safely
        String finishReason = null;
        String dataContent = null;
        if (data != null && !data.isBlank()) {
            try {
                JsonNode root = objectMapper.readTree(data);
                JsonNode rm = root.at("/response_metadata/finish_reason");
                if (!rm.isMissingNode() && !rm.isNull()) {
                    finishReason = rm.asText();
                }
                JsonNode dc = root.at("/data/content");
                if (!dc.isMissingNode() && !dc.isNull()) {
                    dataContent = dc.isTextual() ? dc.asText() : dc.toString();
                }
            } catch (Exception ex) {
                // If not JSON, keep fields null and still store the raw payload
            }
        }
        insertEventRow(eventId, eventOrder, eventName, finishReason, dataContent, data);
    }

    private void insertEventRow(String sseId, int eventOrder, String eventName, String finishReason, String dataContent,
            String fullData) throws SQLException {
        // Commit after each insert: use a fresh connection with auto-commit true.
        try (Connection conn = dataSource.getConnection()) {
            conn.setAutoCommit(true);
            String sql = "INSERT INTO SSE_EVENTS " +
                    "(SSE_ID, EVENT_ORDER, EVENT_NAME, FINISH_REASON, CREATEDATE, DATA_CONTENT, FULL_DATA) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?)";

            try (PreparedStatement ps = conn.prepareStatement(sql)) {
                ps.setString(1, sseId);
                ps.setInt(2, eventOrder);
                if (eventName != null)
                    ps.setString(3, eventName);
                else
                    ps.setNull(3, Types.VARCHAR);
                if (finishReason != null)
                    ps.setString(4, finishReason);
                else
                    ps.setNull(4, Types.VARCHAR);
                ps.setTimestamp(5, Timestamp.from(java.time.Instant.now())); // CREATEDATE = current timestamp
                if (dataContent != null)
                    ps.setString(6, dataContent);
                else
                    ps.setNull(6, Types.VARCHAR);

                // FULL_DATA as CLOB
                if (fullData != null) {
                    ps.setClob(7, new javax.sql.rowset.serial.SerialClob(fullData.toCharArray()));
                } else {
                    ps.setNull(7, Types.CLOB);
                }

                ps.executeUpdate();
                // Auto-commit true ensures commit after each insert
            }
        }

    }
}