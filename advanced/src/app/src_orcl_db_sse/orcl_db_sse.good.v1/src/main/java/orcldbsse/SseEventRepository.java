package orcldbsee;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.commonmark.node.Node;
import org.commonmark.parser.Parser;
import org.commonmark.renderer.html.HtmlRenderer;
import org.commonmark.ext.gfm.tables.TablesExtension;

import java.util.UUID;

import org.commonmark.node.Node;
import org.commonmark.parser.Parser;
import org.commonmark.renderer.html.HtmlRenderer;
import org.commonmark.ext.gfm.tables.TablesExtension; 

import java.util.Arrays;
import java.util.List; 

@Repository
public class SseEventRepository {
    private final JdbcTemplate jdbcTemplate;
    private List extensions = Arrays.asList(TablesExtension.create());
    private HtmlRenderer renderer = HtmlRenderer.builder().extensions(extensions).build();
    private Parser parser = Parser.builder().extensions(extensions).build();

    public SseEventRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public int currentMaxOrderForThread(String threadId) {
        Integer max = jdbcTemplate.queryForObject(
                "SELECT COALESCE(MAX(EVENT_ORDER),0) FROM SSE_EVENTS WHERE THREAD_ID = ?",
                Integer.class,
                threadId);
        return (max == null) ? 0 : max;
    }

    public String markdownToHtml(String markdown) {
        Node document = parser.parse(markdown);
        return renderer.render(document);
    }

    public void insertEvent(String sseId,
            String threadId,
            int eventOrder,
            String eventName,
            String finishReason,
            String type,
            String name,
            String dataContent,
            String fullData) {
        jdbcTemplate.update(con -> {
            if (fullData != null) {
                IO.println("dataContent=" + dataContent);
                IO.println("fullData.length()=" + fullData.length());
            }
            String htmlContent = null;
            if (dataContent != null) {
                htmlContent = markdownToHtml(dataContent);
            }

            var ps = con.prepareStatement(
                    "INSERT INTO SSE_EVENTS " +
                            "(SSE_ID, THREAD_ID, EVENT_ORDER, EVENT_NAME, FINISH_REASON, CREATEDATE, TYPE, NAME, DATA_CONTENT, HTML_CONTENT, FULL_DATA) "
                            +
                            "VALUES (?, ?, ?, ?, ?, SYSTIMESTAMP, ?, ?, ?, ?, ?)");
            ps.setString(1, sseId != null ? sseId : UUID.randomUUID().toString());
            ps.setString(2, threadId);
            ps.setInt(3, eventOrder);
            ps.setString(4, eventName);
            ps.setString(5, finishReason);
            ps.setString(6, type);
            ps.setString(7, name);
            ps.setString(8, dataContent);
            ps.setString(9, htmlContent);
            ps.setString(10, fullData);
            return ps;
        });
    }

}