package orcldbsee;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

@RestController
public class SseController {
    private final SseIngestService service;

    public SseController(SseIngestService service) {
        this.service = service;
    }

    // Example: POST /startsse?thread_id=abc123
    @PostMapping(path = "/startsse")
    public Mono<ResponseEntity<String>> startSse(@RequestParam("thread_id") String threadId,
            @RequestBody String jsonBody) {
        return service.start(threadId, jsonBody)
                // We immediately return Accepted to indicate the ingestion has started
                // asynchronously
                .thenReturn(ResponseEntity.status(HttpStatus.ACCEPTED)
                        .body("SSE ingestion started for thread_id=" + threadId));
    }
}