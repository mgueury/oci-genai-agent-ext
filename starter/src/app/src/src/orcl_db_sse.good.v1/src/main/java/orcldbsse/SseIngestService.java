package orcldbsee;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.http.codec.ServerSentEvent;
import reactor.core.publisher.Mono;
import reactor.core.publisher.Flux;
import reactor.core.scheduler.Schedulers;
import reactor.netty.http.client.HttpClient;
import reactor.core.Disposable;

import java.time.Duration;
import java.util.*;
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
    private HashMap<String, Integer> lastIdxMap = new HashMap<>();

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

    public Flux<ServerSentEvent> start(String threadId, String jsonBody) {
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

        return baseClient.post()
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
                                    Integer lastIdx = lastIdxMap.containsKey(threadId) ? lastIdxMap.get(threadId) : 0;
                                    for (int idx = lastIdx; idx < messages.size(); idx++) {
                                        IO.println("message.size=" + messages.size() +" / idx=" + idx);
                                        JsonNode lastMessage = messages.get(messages.size() - 1);
                                        fullData = objectMapper.writeValueAsString(lastMessage);
                                        type = lastMessage.path("type").asText(null);
                                        name = lastMessage.path("name").asText(null);
                                        JsonNode content = lastMessage.path("content");
                                        JsonNode toolCalls = lastMessage.path("tool_calls");
                                        IO.println("type=" + type);
                                        IO.println("name=" + name);
                                        if (type.equals("tool") ) {
                                            IO.println("tool_result");
                                            dataContent = "*Tool Result*\n";
                                            dataContent += "\n| " + name + " |\n";
                                            dataContent += "| ----- |\n";
                                            dataContent += "| <div class='citation'> + <span class='hide'>"
                                                    + content.get(0).path("text").asText(null) + "</span></div> |\n";
                                        } else if (content.isArray() && content.size() > 0) {
                                            dataContent = content.get(0).path("text").asText(null);
                                        } else if (toolCalls.isArray() && toolCalls.size() > 0) {
                                            dataContent = "*Tool Calls*\n";
                                            for (JsonNode tool : toolCalls) {
                                                if (tool.isObject()) {
                                                    dataContent += "\n| " + tool.path("name").asText("none") + " |\n";
                                                    dataContent += "| ----- |\n";
                                                    JsonNode args = tool.path("args");
                                                    if (args.isObject()) {
                                                        Iterator<Map.Entry<String, JsonNode>> fields = args.fields();
                                                        while (fields.hasNext()) {
                                                            Map.Entry<String, JsonNode> f = fields.next();
                                                            dataContent += "| " + f.getKey() + " = "
                                                                    + f.getValue().toString() + " |\n";
                                                        }
                                                    }
                                                } else {
                                                    dataContent += "Element is not an object: " + tool;
                                                }
                                            }
                                        } else {
                                            dataContent = content.asText(null);
                                        }
                                        finishReason = lastMessage.path("additional_kwargs").path("finish_reason")
                                                .asText(null);
                                        if (dataContent != null && dataContent != "") {
                                            repository.insertEvent(sseId, threadId, order, eventName, finishReason,
                                                    type, name,
                                                    dataContent, fullData);
                                        }
                                        lastIdxMap.put(threadId, idx + 1);
                                    }

                                }
                            } catch (Exception e) {
                                IO.println("Exeption: " + e.getMessage());
                                e.printStackTrace();
                            }
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }).doOnError(Throwable::printStackTrace); // fire-and-forget
    }
}
