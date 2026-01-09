package orcldbsee.controller;

import jakarta.servlet.http.HttpServletResponse;
import orcldbsee.service.SseService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
public class SseController {
    private final SseService sseService;
    private final WebClient langGraphClient;

    @Value("${LANGGRAPH_APIKEY:}")
    private String langGraphApiKey;

    public SseController(SseService sseService, WebClient langGraphWebClient) {
        this.sseService = sseService;
        this.langGraphClient = langGraphWebClient;
    }

    // POST /sse?thread_id=xxxx
    // Body: JSON payload; returns an SSE stream
    @PostMapping(path = "/sse", consumes = MediaType.APPLICATION_JSON_VALUE)
    public SseEmitter startSse(
            @RequestParam("thread_id") String threadId,
            @RequestBody(required = false) String body,
            HttpServletResponse response) {

        if (threadId == null || threadId.isBlank()) {
            throw new IllegalArgumentException("thread_id is required");
        }

        // Check thread exists in memory map
        if (!sseService.isKnownThread(threadId)) {
            response.setStatus(403);
            throw new IllegalArgumentException("Unknown or unauthorized thread_id");
        }

        // Start proxying SSE and persisting events
        return sseService.startProxySse(threadId, body);
    }

    // POST /thread?API_KEY=xxxx
    // Returns text/plain: thread_id
    @PostMapping(path = "/thread", produces = MediaType.TEXT_PLAIN_VALUE)
    public String createThread(@RequestParam("API_KEY") String apiKey) {
        if (apiKey == null || apiKey.isBlank()) {
            throw new IllegalArgumentException("API_KEY is required");
        }
        if (!apiKey.equals(langGraphApiKey)) {
            throw new SecurityException("Invalid API_KEY");
        }
        return sseService.createThreadAndStore(langGraphClient);
    }

}