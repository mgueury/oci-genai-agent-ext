package orcldbsee; 

import org.springframework.http.MediaType;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.http.codec.ServerSentEvent;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;
import reactor.netty.http.client.HttpClient; 

import java.time.Duration;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger; 

@Service
public class SseIngestService { 
private final SseEventRepository repository;
private final WebClient baseClient;

// Track per-thread event order
private final Map<String, AtomicInteger> threadOrderCounters = new ConcurrentHashMap<>();

public SseIngestService(SseEventRepository repository) {
    this.repository = repository;

    HttpClient httpClient = HttpClient.create()
            .responseTimeout(Duration.ofMinutes(5));

    this.baseClient = WebClient.builder()
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .build();
}

public Mono<Void> start(String threadId, String jsonBody) {
    if (request == null || request.getSseUrl() == null || request.getSseUrl().isBlank()) {
        return Mono.error(new IllegalArgumentException("sseUrl must be provided in the request body"));
    }

    // Initialize event order counter from DB max for this thread
        threadOrderCounters.computeIfAbsent(threadId, t -> new AtomicInteger(repository.currentMaxOrderForThread(threadId)));

    String base = System.getenv("LANGGRAPH_URL");
    String normBase = base.endsWith("/") ? base.substring(0, base.length() - 1) : base;
    String encodedThreadId = URLEncoder.encode(threadId, StandardCharsets.UTF_8);
    String sseUrl = normBase + "/threads/" + encodedThreadId + "/runs/stream";

    WebClient client = baseClient.mutate()
            .baseUrl(sseUrl)
            .defaultHeaders(h -> {
                h.setAccept(java.util.List.of(MediaType.TEXT_EVENT_STREAM));
                Map<String, String> headers = request.getHeaders();
                if (headers != null) {
                    headers.forEach(h::add);
                }
            })
            .build();

    // Start consuming SSE. We subscribe on a boundedElastic scheduler so JDBC calls don't block event loops.
    return client.get()
            .accept(MediaType.TEXT_EVENT_STREAM)
            .retrieve()
            .bodyToFlux(ServerSentEvent.class)
            .publishOn(Schedulers.boundedElastic())
            .doOnNext(evt -> {
                try {
                    String sseId = evt.id() != null ? evt.id().toString() : UUID.randomUUID().toString();
                    String eventName = evt.event() != null ? evt.event() : "message";
                    String data = evt.data() != null ? String.valueOf(evt.data()) : null;
                    String fullData = data; // If you need raw lines, keep same for now
                    String finishReason = null;

                    int order = threadOrderCounters.get(threadId).incrementAndGet();
                    repository.insertEvent(sseId, threadId, order, eventName, finishReason, data, fullData);
                } catch (Exception e) {
                    // Log and continue; in real apps, use a logger
                    e.printStackTrace();
                }
            })
            .doOnError(err -> {
                // Log error; in real apps use Logger and possibly persist an error entry
                err.printStackTrace();
            })
            .then();
}

} 