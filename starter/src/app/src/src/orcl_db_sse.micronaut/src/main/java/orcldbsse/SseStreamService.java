package orcldbsse;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micronaut.context.annotation.Value;
import io.micronaut.http.MediaType;
import io.micronaut.http.MutableHttpRequest;
import io.micronaut.http.client.HttpClient;
import io.micronaut.http.client.annotation.Client;
import io.micronaut.http.sse.Event;
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
public class SseStreamService {

    @Value("${langgraph.url}")
    String langgraphUrl;

    private final HttpClient httpClient;
    private final DataSource dataSource;
    private final ObjectMapper objectMapper;

    @Inject
    @Client("/") // base-less client; absolute URLs are allowed
    SseClient sseClient;

    @Inject
    public SseStreamService(@Client("/") HttpClient httpClient, DataSource dataSource, ObjectMapper objectMapper) {
        this.httpClient = httpClient;
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
    }

    public void startAndIngest(String threadId, JsonNode body) {
        try {
            String sseUrl = this.langgraphUrl + "/threads/" + threadId + "/runs/stream";
            String streamId = java.util.UUID.randomUUID().toString();
            java.util.concurrent.atomic.AtomicInteger order = new java.util.concurrent.atomic.AtomicInteger(0);

            MutableHttpRequest<JsonNode> request = io.micronaut.http.HttpRequest
                    .POST(sseUrl, body) // absolute URL
                    .contentType(MediaType.APPLICATION_JSON_TYPE)
                    .accept(MediaType.TEXT_EVENT_STREAM_TYPE);

            reactor.core.publisher.Flux.from(sseClient.eventStream(request, byte[].class))
                    .subscribe(event -> {
                        try {
                            String data = event.getData() != null
                                    ? new String(event.getData(), java.nio.charset.StandardCharsets.UTF_8)
                                    : null;
                            handleEvent(threadId, streamId, order.incrementAndGet(),
                                    event.getId(), event.getName(), data);
                        } catch (Exception e) {
                            IO.println("<startAndIngest>Exception:" + e.getMessage());
                            e.printStackTrace();
                        }
                    }, Throwable::printStackTrace);
            /*
             * reactor.core.publisher.Flux.from(sseClient.eventStream(request,
             * String.class))
             * .subscribe(event -> {
             * try {
             * handleEvent(streamId, threadId, order.incrementAndGet(), event);
             * } catch (Exception e) {
             * IO.println("<startAndIngest>Exception:" + e.getMessage());
             * e.printStackTrace();
             * }
             * }, throwable -> {
             * throwable.printStackTrace();
             * });
             */
        } catch (Exception e) {
            IO.println("<startAndIngest>Exception:" + e.getMessage());
            e.printStackTrace();
        }
    }

    private void handleEvent(String streamId, String threadId, int eventOrder, String eventId, String eventName, String data) throws Exception {
        IO.println("<handleEvent>");
        IO.println("eventName: " + eventName);
        IO.println("eventId: " + eventId);
        if (eventId == null || eventId.isBlank()) {
            eventId = streamId;
        }
        IO.println("data: " + data);

        String finishReason = null;
        String dataContent = null;
        if (data != null && !data.isBlank()) {
            try {
                com.fasterxml.jackson.databind.JsonNode root = objectMapper.readTree(data);
                var rm = root.at("/response_metadata/finish_reason");
                if (!rm.isMissingNode() && !rm.isNull()) {
                    finishReason = rm.asText();
                }
                var dc = root.at("/data/content");
                if (!dc.isMissingNode() && !dc.isNull()) {
                    dataContent = dc.isTextual() ? dc.asText() : dc.toString();
                }
            } catch (Exception e) {
                IO.println("<handleEvent>Exception when reading the JSON payload:" + e.getMessage());
                e.printStackTrace();
            }
        }
        insertEventRow(eventId, threadId, eventOrder, eventName, finishReason, dataContent, data);
    }

    private void insertEventRow(String sseId, String threadId, int eventOrder, String eventName, String finishReason,
            String dataContent,
            String fullData) throws SQLException {
        // Commit after each insert: use a fresh connection with auto-commit true.
        try (Connection conn = dataSource.getConnection()) {
            conn.setAutoCommit(true);
            String sql = "INSERT INTO SSE_EVENTS " +
                    "(SSE_ID, THREAD_ID, EVENT_ORDER, EVENT_NAME, FINISH_REASON, CREATEDATE, DATA_CONTENT, FULL_DATA) "
                    +
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)";

            try (PreparedStatement ps = conn.prepareStatement(sql)) {
                ps.setString(1, sseId);
                ps.setString(2, threadId);
                ps.setInt(3, eventOrder);
                if (eventName != null)
                    ps.setString(4, eventName);
                else
                    ps.setNull(4, Types.VARCHAR);
                if (finishReason != null)
                    ps.setString(5, finishReason);
                else
                    ps.setNull(5, Types.VARCHAR);
                ps.setTimestamp(6, Timestamp.from(java.time.Instant.now())); // CREATEDATE = current timestamp
                if (dataContent != null)
                    ps.setString(7, dataContent);
                else
                    ps.setNull(7, Types.VARCHAR);
                if (fullData != null) {
                    ps.setString(8, fullData);
                } else {
                    ps.setNull(8, Types.CLOB);
                }

                ps.executeUpdate();
                // Auto-commit true ensures commit after each insert
            }
        }

    }
}