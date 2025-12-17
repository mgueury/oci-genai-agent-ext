package orcldbsee;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import reactor.core.publisher.Flux;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.*;

@Service
public class SseService {
    private final WebClient langGraphClient;
    private final SseDataRepository repo;
    private final ExecutorService asyncDbExecutor = Executors.newFixedThreadPool(4);

    // Global in-memory registry of allowed thread IDs
    // Value is a simple Boolean flag
    private final ConcurrentMap<String, Boolean> g_threadHashMap = new ConcurrentHashMap<>();

    public SseService(WebClient langGraphWebClient, SseDataRepository repo) {
        this.langGraphClient = langGraphWebClient;
        this.repo = repo;
    }

    public boolean isKnownThread(String threadId) {
        return g_threadHashMap.containsKey(threadId);
    }

    public SseEmitter startProxySse(String threadId, String jsonBody) {
        SseEmitter emitter = new SseEmitter(0L); // no timeout; adjust if needed

        ParameterizedTypeReference<ServerSentEvent<String>> type = new ParameterizedTypeReference<>() {
        };

        Flux<ServerSentEvent<String>> flux = langGraphClient.post()
                .uri(uriBuilder -> uriBuilder.path("/threads/{threadId}/runs/stream")
                        .build(threadId))
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(jsonBody)
                .retrieve()
                .bodyToFlux(type);

        flux.subscribe(
                sse -> {
                    try {
                        // Forward to caller
                        SseEmitter.SseEventBuilder ev = SseEmitter.event();
                        if (sse.id() != null)
                            ev.id(sse.id());
                        if (sse.event() != null)
                            ev.name(sse.event());
                        Object dataObj = sse.data();
                        String dataStr = dataObj == null ? "" : dataObj.toString();
                        ev.data(dataStr, MediaType.TEXT_PLAIN);
                        emitter.send(ev);

                        // Async persist
                        asyncDbExecutor.submit(() -> safeInsert(threadId,
                                sse.id(),
                                sse.event(),
                                dataStr));
                    } catch (Exception e) {
                        emitter.completeWithError(e);
                    }
                },
                error -> emitter.completeWithError(error),
                emitter::complete);

        return emitter;
    }

    private void safeInsert(String threadId, String eventId, String eventName, String eventData) {
        try {
            repo.insertEvent(threadId, eventId, eventName, eventData);
        } catch (Exception e) {
            // log minimal; in real app, use a logger
            System.err.println("DB insert failed: " + e.getMessage());
        }
    }

    public String createThreadAndStore(WebClient langGraphClient) {
        // GET $LANGGRAPH_URL/thread -> { "thread_id": "..." }
        record ThreadResponse(String thread_id) {
        }
        ThreadResponse tr = langGraphClient.get()
                .uri("/threads")
                .retrieve()
                .bodyToMono(ThreadResponse.class)
                .block();

        if (tr == null || tr.thread_id == null || tr.thread_id.isBlank()) {
            throw new IllegalStateException("Invalid response from LANGGRAPH /thread");
        }

        String threadId = tr.thread_id();
        g_threadHashMap.put(threadId, Boolean.TRUE);

        // Store the thread creation as an event row
        try {
            repo.insertEvent(threadId, threadId, "THREAD_CREATED", threadId);
        } catch (Exception e) {
            System.err.println("DB insert (thread) failed: " + e.getMessage());
        }

        return threadId;
    }

}