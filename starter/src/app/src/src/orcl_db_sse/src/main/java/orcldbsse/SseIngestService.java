package orcldbsee;

import org.springframework.http.MediaType;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.http.codec.ServerSentEvent;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;
import reactor.netty.http.client.HttpClient;
import reactor.core.Disposable;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.nio.charset.StandardCharsets;
import java.net.URLEncoder;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

@Service
public class SseIngestService {
    private final SseEventRepository repository;
    private final WebClient baseClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

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

    public void startAsync(String threadId, String jsonBody) {
        // Initialize event order counter from DB max for this thread
        threadOrderCounters.computeIfAbsent(threadId,
                t -> new AtomicInteger(repository.currentMaxOrderForThread(threadId)));

        String base = System.getenv("LANGGRAPH_URL");
        String normBase = base.endsWith("/") ? base.substring(0, base.length() - 1) : base;
        String encodedThreadId = URLEncoder.encode(threadId, StandardCharsets.UTF_8);
        String sseUrl = normBase + "/threads/" + encodedThreadId + "/runs/stream";
        IO.println("base=" + base);
        IO.println("sseUrl=" + sseUrl);
        IO.println("jsonBody=" + jsonBody);

        Disposable sub = baseClient.post()
                .uri(sseUrl)
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(jsonBody) // forward payload exactly as received
                .retrieve()
                .bodyToFlux(ServerSentEvent.class)
                .publishOn(Schedulers.boundedElastic())
                .doOnNext(evt -> {
                    try {
                        String sseId = evt.id();
                        String eventName = evt.event();
                        Object data = evt.data();
                        String dataContent = null;
                        String finishReason = null;
                        String fullData = null;
                        String name = null;
                        String type = null;
                        int order = threadOrderCounters.get(threadId).incrementAndGet();

                        if (data != null) {
                            IO.println("class=" + evt.getClass().getSimpleName());
                            IO.println("data class=" + evt.data().getClass().getSimpleName());
                            objectMapper.writeValueAsString(data);

                            // Try to parse JSON
                            try {
                                JsonNode root = objectMapper.valueToTree(data);
                                fullData = objectMapper.writeValueAsString(root);
                                JsonNode messages = root.path("messages");
                                if (messages.isArray() && messages.size() > 0) {
                                    int idx = messages.size() - 1;
                                    JsonNode lastMessage = messages.get(messages.size() - 1);
                                    fullData = objectMapper.writeValueAsString(lastMessage);
                                    type = lastMessage.path("type").asText(null);
                                    name = lastMessage.path("name").asText(null);
                                    JsonNode content = lastMessage.path("content");
                                    if (content.isArray() && content.size() > 0) {  
                                       dataContent = content.get(0).path("text").asText(null);
                                    }  else {
                                       dataContent = content.asText(null);
                                    }
                                    finishReason = lastMessage.path("additional_kwargs").path("finish_reason").asText(null);
                                }
                                repository.insertEvent(sseId, threadId, order, eventName, finishReason, name, type, dataContent, fullData);
                            } catch (Exception e) {
                                IO.println("Exeption: " + e.getMessage());
                                e.printStackTrace();
                            }
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                })
                .doOnError(Throwable::printStackTrace)
                .subscribe(); // fire-and-forget
    }
}
