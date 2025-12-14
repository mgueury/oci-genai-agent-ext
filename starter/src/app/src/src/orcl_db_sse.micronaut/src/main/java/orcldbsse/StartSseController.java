package orcldbsse;

import io.micronaut.http.HttpResponse;
import io.micronaut.http.MediaType;
import io.micronaut.http.annotation.*;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.inject.Inject;

@Controller
public class StartSseController {

    @Inject
    SseStreamService sseStreamService;

    @Post("/startsse")
    public HttpResponse<?> startSse(@QueryValue("thread_id") String threadId, @Body JsonNode body) {
        sseStreamService.startAndIngest(threadId, body);
        return HttpResponse.ok("SSE started");
    }
}